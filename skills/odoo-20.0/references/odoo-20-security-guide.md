# Odoo 20 Security Guide

## Coding Conventions

- Define security access in `security/ir.access.csv` (never `ir.model.access.csv`).
- Keep groups and privileges in `security/<module>_groups.xml` and load them before `ir.access.csv` in `__manifest__.py`.
- Name access IDs `access_<model>_<role>` for permissions and `<model>_<role>_rule` or `<model>_comp_rule` for restrictions.
- In `ir.access.csv`, use the model technical name directly (e.g. `sale.order`, not `model_sale_order`).
- For global restrictions (multi-company, multi-website, self-records), leave `group_id/id` blank.
- Use the `'access'` domain operator (e.g. `[('order_id', 'access', 'read')]`) when record access depends on parent model permissions.
- Bind any recordset obtained through `sudo()` to a name ending in `_sudo` (`orders_sudo = self.env['sale.order'].sudo().search(domain)`). Never return a `_sudo` recordset from a public method or keep it on `self`.
- Mark methods that should not be callable via RPC with `@api.private`.

---

## Table of Contents

- [Security Architecture](#security-architecture)
- [Groups & Privileges](#groups--privileges)
- [Unified Access Control (`ir.access`)](#unified-access-control-iraccess)
- [Writing `ir.access.csv`](#writing-iraccesscsv)
- [The 'access' Domain Operator](#the-access-domain-operator)
- [Python Security API](#python-security-api)
- [Field-Level Access](#field-level-access)
- [Security Pitfalls & Best Practices](#security-pitfalls--best-practices)

---

## Security Architecture

In Odoo 20, access control is completely unified under the **`ir.access`** model. The previous two-tier system of `ir.model.access` (model-level ACL) and `ir.rule` (record rules) has been consolidated:

```
┌────────────────────────────────────────────────────────┐
│                      ir.access                         │
├──────────────────────────┬─────────────────────────────┤
│   Permissions (group_id) │   Restrictions (no group_id)│
│   Grants access for role │   Global security filters   │
│   Combined via OR        │   Combined via AND          │
└──────────────────────────┴─────────────────────────────┘
```

When evaluating whether a user can perform an operation (`read`, `write`, `create`, `unlink`):
1. User must have at least one **Permission** granting the operation on the model (or subset matching a permission domain). All matching permissions are combined with **`OR`**.
2. All **Restrictions** (entries with no `group_id`, such as multi-company rules) must be satisfied. All restrictions are combined with **`AND`**.
3. Formula: `Domain.OR(permissions) & Domain.AND(restrictions)`.

---

## Groups & Privileges

Groups (`res.groups`) organize users and associate with access rights. Odoo uses a privilege-based hierarchy:

```
ir.module.category → res.groups.privilege → res.groups → res.users
```

### Defining Groups & Privileges

File: `security/my_module_groups.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Privilege definition -->
    <record id="privilege_my_module" model="res.groups.privilege">
        <field name="name">My Module Management</field>
        <field name="category_id" ref="base.module_category_services"/>
    </record>

    <!-- User Group -->
    <record id="group_my_module_user" model="res.groups">
        <field name="name">User</field>
        <field name="privilege_id" ref="privilege_my_module"/>
        <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <!-- Manager Group -->
    <record id="group_my_module_manager" model="res.groups">
        <field name="name">Administrator</field>
        <field name="privilege_id" ref="privilege_my_module"/>
        <field name="implied_ids" eval="[(4, ref('group_my_module_user'))]"/>
        <field name="users" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
    </record>
</odoo>
```

---

## Unified Access Control (`ir.access`)

### Fields of `ir.access`

| Field | Type | Description |
|-------|------|-------------|
| `id` | Char (external ID) | Unique XML ID of the access rule |
| `name` | Char | Human-readable description |
| `model_id` | Many2one (`ir.model`) | Model technical name (e.g. `my.model`) |
| `group_id` | Many2one (`res.groups`) | Group granting permission. If empty, rule is a global restriction |
| `operation` | Selection | Operations covered, subset of `crud` (`r`, `ru`, `cru`, `crud`, `c`, `d`, etc.) |
| `domain` | Char | Domain expression constraining the access |
| `kind` | Selection (computed) | `'permission'` (if `group_id` is set) or `'restriction'` (if `group_id` is empty) |

### Operations (`operation`)

- `c` = Create
- `r` = Read
- `u` = Update (Write)
- `d` = Delete (Unlink)

Combinations:
- `r`: Read-only
- `ru`: Read and write
- `cru`: Create, read, and write (standard user)
- `crud`: Full access (create, read, update, delete)

---

## Writing `ir.access.csv`

File: `security/ir.access.csv`

```csv
id,name,model_id,group_id/id,operation,domain
access_my_model_user,my.model.user,my.model,my_module.group_my_module_user,cru,
access_my_model_manager,my.model.manager,my.model,my_module.group_my_module_manager,crud,
my_model_personal_rule,Personal Records,my.model,my_module.group_my_module_user,cru,"['|', ('user_id', '=', user.id), ('user_id', '=', False)]"
my_model_comp_rule,My Model multi-company,my.model,,crud,"[('company_id', 'in', company_ids)]"
```

### Important Differences from Odoo 19 & earlier:
1. File is **`ir.access.csv`** (never `ir.model.access.csv`).
2. Header column is **`model_id`** with direct model technical name (e.g. `my.model`), **NOT** `model_id:id` with `model_my_model`.
3. Header column for groups is **`group_id/id`**.
4. Single **`operation`** column with letters `c`, `r`, `u`, `d` replaces four separate `perm_read`, `perm_write`, `perm_create`, `perm_unlink` columns.
5. Domain is embedded directly in the CSV via **`domain`** column. No separate `<record model="ir.rule">` is needed!
6. For global rules (restrictions), leave `group_id/id` blank.

---

## The 'access' Domain Operator

In Odoo 20, child records can delegate their access checks to parent records using the `'access'` operator:

```csv
id,name,model_id,group_id/id,operation,domain
my_order_line_rule_portal,Portal Order Line,my.order.line,base.group_portal,r,"[('order_id', 'access', 'read')]"
my_order_line_comp_rule,Order Line multi-company,my.order.line,,crud,"[('order_id', 'access', 'write')]"
```

Syntax: `('relational_field', 'access', 'operation')`
- Valid operations: `'read'`, `'write'`, `'create'`, `'unlink'`.
- Eliminates redundant SQL joins and duplicate logic in child record rules.

---

## Python Security API

### Checking Access in Python

Always use the standard modern methods:

```python
# Check if user has access (raises AccessError if not allowed)
self.check_access('read')
self.check_access('write')
self.check_access('create')
self.check_access('unlink')

# Test boolean permission without raising
if self.has_access('write'):
    self.write({'state': 'done'})

# Filter recordset to records current user can access
allowed_records = self._filtered_access('read')

# Field-level access check
self.check_field_access(self._fields['salary'], 'read')
```

> **Odoo 20 Changes**:
> - `check_field_access(field, operation)` replaces deprecated `_check_field_access()`.
> - `Model._access_domain(operation)` replaces deprecated `_check_access(operation)`.
> - `self.env.invalidate_access_cache()` replaces deprecated `clear_access_cache()`.

### Overriding Security Logic

To customize security domains programmatically, override `_access_domain`:

```python
@api.model
def _access_domain(self, operation: str) -> Domain:
    domain = super()._access_domain(operation)
    if not self.env.is_admin() and operation == 'write':
        domain &= Domain('state', '!=', 'locked')
    return domain
```

### Safe Usage of `sudo()`

```python
# Good: Explicit suffix, narrow scope, never leaked
partner_sudo = self.partner_id.sudo()
balance = partner_sudo.credit_limit

# Good: One-shot write without assigning to variable
record.sudo().write({'internal_sequence': next_seq})

# Bad: Storing sudo on self or returning sudo recordset to caller
self.sudo().partner_id  # Avoid leaking sudo
```

### Protecting Methods with `@api.private`

Public methods (not prefixed with `_`) that should never be exposed over RPC must be decorated with `@api.private`:

```python
from odoo import api, models

class MyModel(models.Model):
    _name = 'my.model'

    @api.private
    def compute_internal_secret(self):
        """Cannot be triggered over external JSON-RPC / XML-RPC."""
        ...
```

---

## Field-Level Access

Restrict field visibility and editability using `groups=`:

```python
salary = fields.Float(
    string="Salary",
    groups="hr.group_hr_manager",  # Only HR managers can read or write
)

cost_price = fields.Monetary(
    string="Cost Price",
    groups="purchase.group_purchase_manager",
)
```

---

## Security Pitfalls & Best Practices

1. **Manifest File**:
   Include `'security/ir.access.csv'` in `__manifest__.py` under `data`:
   ```python
   'data': [
       'security/my_module_groups.xml',
       'security/ir.access.csv',
       'views/my_model_views.xml',
   ],
   ```
2. **Never rely on UI restrictions alone**:
   Attributes like `invisible="not is_admin"` or `readonly="1"` in views are UI-only. Always enforce server-side via `ir.access.csv` or `groups=` on fields.
3. **Always specify `domain` for multi-company records**:
   ```csv
   my_model_comp_rule,My Model Multi-Company,my.model,,crud,"[('company_id', 'in', company_ids)]"
   ```
4. **Use `@api.readonly` on query methods**:
   Methods that only read data should be decorated with `@api.readonly` for automatic savepoint isolation and read-replica routing.

