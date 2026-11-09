# Odoo 20 Migration Guide

Guide for migrating modules from Odoo 19 to Odoo 20.

## Table of Contents

- [Overview & Migration Strategy](#overview--migration-strategy)
- [Key Breaking Changes Summary](#key-breaking-changes-summary)
- [Security Migration (`ir.access`)](#security-migration-iraccess)
- [Frontend Migration (Owl 2 to Owl 3)](#frontend-migration-owl-2-to-owl-3)
- [ORM & Python Backend Migration](#orm--python-backend-migration)
- [Views & XML Data Migration](#views--xml-data-migration)
- [Using `odoo-bin upgrade_code`](#using-odoo-bin-upgrade_code)
- [Verification Checklist](#verification-checklist)

---

## Overview & Migration Strategy

1. **Prerequisites**: Ensure local environment runs Python 3.12+ and PostgreSQL 16+.
2. **Automated Conversion**: Run the built-in Odoo code upgrader `odoo-bin upgrade_code`.
3. **Manual Adaptations**: Update security definitions to `ir.access.csv` and OWL 3 component declarations.
4. **Testing**: Run Python tests and OWL Hoot tests.

---

## Key Breaking Changes Summary

| Subsystem | Odoo 19 | Odoo 20 |
|-----------|---------|---------|
| **Security Files** | `ir.model.access.csv` + `ir.rule` | Single `security/ir.access.csv` |
| **Security Model Column** | `model_id:id` (`model_sale_order`) | `model_id` (`sale.order`) |
| **Security Method** | `_check_field_access()` | `check_field_access()` |
| **Security Access Domain** | `_check_access(operation)` | `_access_domain(operation)` |
| **Record Search Names** | `_rec_names_search = ['name']` (list) | `_rec_names_search = ('name',)` (tuple) |
| **Field Column Init** | Override `_init_column()` | Field parameter `init_storage='...'` |
| **ORM Cache Clear** | `registry.clear_cache()` | `self.env.transaction.invalidate_ormcache()` |
| **Env Clear** | `self.env.clear()` | `self.env.transaction.clear()` / `reset()` |
| **Cache Import** | `from odoo.tools.cache import ormcache` | `from odoo.api import ormcache` |
| **SQL Escaping** | `escape_psql()` | `escape_like_value()` |
| **XML Binary File** | `<field type="base64" file="..."/>` | `<field type="bytes" file="..."/>` |
| **Search Date Filter** | `start_month="-1" end_month="0"` | Range attributes removed |
| **OWL Props** | `static props = { ... }` | `props = useProps({ ... })` |
| **OWL State** | `useState({ ... })` | `proxy({ ... })` or signals |
| **OWL Services** | `useService('name')` | `usePlugin(PluginClass)` as class fields |
| **OWL Slots** | `<t t-slot="..."/>` | `<t t-call-slot="..."/>` |
| **OWL Template Vars** | `<t t-out="name"/>` | `<t t-out="this.name"/>` (`this.` prefix required) |
| **Route Type** | `type='json'` (deprecated) | `type='jsonrpc'` |

---

## Security Migration (`ir.access`)

### Step 1: Rename File
Rename `security/ir.model.access.csv` to `security/ir.access.csv` and update `__manifest__.py`.

### Step 2: Convert Model ID & Operations
Replace the 4 permission columns (`perm_read,perm_write,perm_create,perm_unlink`) with a single `operation` column. Change `model_id:id` with `model_<model>` to `model_id` with `<model>`.

**Before (v19):**
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_model_user,my.model.user,model_my_model,group_user,1,1,1,0
```

**After (v20):**
```csv
id,name,model_id,group_id/id,operation,domain
access_my_model_user,my.model.user,my.model,my_module.group_user,cru,
```

### Step 3: Migrate XML `<record model="ir.rule">` into `ir.access.csv`
Move record rules into `ir.access.csv` by populating the `domain` column. Global rules leave `group_id/id` empty:

```csv
my_model_comp_rule,My Model Multi-Company,my.model,,crud,"[('company_id', 'in', company_ids)]"
```

---

## Frontend Migration (Owl 2 to Owl 3)

### Step 1: Update Props
Replace static `props` with `useProps`:

```javascript
// Before (v19)
export class MyWidget extends Component {
    static props = {
        title: { type: String, optional: true },
    };
}

// After (v20)
import { Component, t, useProps } from "@odoo/owl";

export class MyWidget extends Component {
    props = useProps({
        title: t.string().optional(),
    });
}
```

### Step 2: Replace `useState` with `proxy`
```javascript
// Before (v19)
this.state = useState({ count: 0 });

// After (v20)
import { proxy } from "@odoo/owl";
this.state = proxy({ count: 0 });
```

### Step 3: Replace Services with Plugins
```javascript
// Before (v19)
setup() {
    this.action = useService("action");
}

// After (v20)
import { usePlugin } from "@odoo/owl";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class MyWidget extends Component {
    action = usePlugin(ActionPlugin);
}
```

### Step 4: Add `this.` in Templates
Update all XML templates so every component state, property, or method uses `this.`:

```xml
<!-- Before (v19) -->
<button t-on-click="onClick"><t t-out="props.title"/></button>

<!-- After (v20) -->
<button t-on-click="this.onClick"><t t-out="this.props.title"/></button>
```

---

## ORM & Python Backend Migration

1. **Update `_rec_names_search`**:
   ```python
   # Before (v19):
   _rec_names_search = ['name', 'code']

   # After (v20):
   _rec_names_search = ('name', 'code')
   ```

2. **Update Cache Invalidation**:
   ```python
   # Before (v19):
   self.env.registry.clear_cache()
   self.env.clear()

   # After (v20):
   self.env.transaction.invalidate_ormcache()
   self.env.transaction.clear()
   ```

3. **Update Security Checks**:
   ```python
   # Before (v19):
   self._check_field_access(field, 'read')

   # After (v20):
   self.check_field_access(field, 'read')
   ```

---

## Views & XML Data Migration

1. **Remove Range Attributes from Date Filters**:
   ```xml
   <!-- Before (v19) -->
   <filter name="date" date="date" start_month="-2" end_month="0"/>

   <!-- After (v20) -->
   <filter name="date" date="date"/>
   ```

2. **Replace `type="base64"` with `type="bytes"` in XML Data**:
   ```xml
   <!-- Before (v19) -->
   <field name="datas" type="base64" file="my_mod/data/doc.pdf"/>

   <!-- After (v20) -->
   <field name="datas" type="bytes" file="my_mod/data/doc.pdf"/>
   ```

---

## Using `odoo-bin upgrade_code`

Odoo 20 includes automated code transformation scripts:

```bash
# Run automated code upgrades on custom addons directory
python3 odoo-bin upgrade_code -p /path/to/custom_addons
```

This runs:
- `owl3-migration.py` (converts `useService`, `t-slot`, `t-esc`, template variables)
- `20.0-00-search-date-filters.py` (removes date range filter attributes)
- `19.4-00-ir-access.py` (converts ACLs and rules to `ir.access`)
- `19.5-00-tuple-rec_names_search.py` (converts `_rec_names_search` to tuples)

---

## Verification Checklist

- [ ] `security/ir.access.csv` exists and replaces `ir.model.access.csv`
- [ ] No `<record model="ir.rule">` remains in XML files
- [ ] `_rec_names_search` is declared as a tuple on all models
- [ ] All OWL components declare props with `useProps` and state with `proxy`
- [ ] All OWL templates use `this.` for component variables and `<t t-call-slot="..."/>`
- [ ] No `type="base64"` in XML data files
- [ ] Tests run and pass without deprecation warnings

