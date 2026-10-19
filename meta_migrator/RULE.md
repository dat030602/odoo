# RULE.md — Meta Migrator AI Data Generation & Scenario Blueprint (Odoo 19)

> **Purpose:** This document is the definitive, standalone operational guide for AI agents to design, construct, and seed migration scenarios, jobs, steps, runs, and change diffs in module `meta_migrator` (Odoo 19).  
> **Rule of Thumb:** An AI agent reading this single file has **100% of the knowledge required** to generate valid data without reading the rest of the module codebase.

---

## 1. System Architecture & Entity Hierarchy

```
meta.migration.connection (Remote or Local Odoo XML-RPC endpoints)
       │
       ▼
meta.migration.job        (Reusable migration scenario configuration)
 ├── step_ids ──────────► meta.migration.step   (Ordered execution blueprint)
 └── run_ids  ──────────► meta.migration.run    (Execution instance: Test or Run)
                           └── change_ids ──────► meta.migration.change (Read-only Diff UI)
```

### Core Entity Responsibilities
1. **`meta.migration.connection`**: Stores XML-RPC credentials (`url`, `db`, `username`, `password`).
2. **`meta.migration.job`**: Defines **what** to migrate (`step_ids`), default `source_connection_id` & `target_connection_id`, conflict policy (`on_conflict`), and execution flags. Contains no business state.
3. **`meta.migration.step`**: Pure configuration payload defining a single migration action. **Has no relational dependencies on the local database** (`ir.model`, `ir.ui.view` etc. are never referenced as Many2one).
4. **`meta.migration.run`**: An execution snapshot (`mode='test'` for dry-run diffing or `mode='run'` for live push).
5. **`meta.migration.change`**: Read-only comparison record rendered by OWL Diff widgets (`MetaModelCreate`, `MetaFieldUpdate`, `CodeDiff`, etc.).

---

## 2. Allowed Actions Matrix (`ALLOWED_ACTIONS`)

| Object Type (`object_type`) | Allowed Actions (`action`) | Mandatory Key Input | Notes |
| :--- | :--- | :--- | :--- |
| **`model`** | `create` only | `model_name` | Creates model or checks differences if already exists. |
| **`field`** | `create` only | `model_name` | Creates field or updates attributes if already exists. |
| **`view`** | `create`, `update` | `model_name` + `view_type` (create)<br>`xml_id` (update) | `create` generates a new view.<br>`update` appends elements to an existing view via XPath. |
| **`server_action`** | `create`, `update` | `xml_id` | `create` declares a new action.<br>`update` overrides code/bindings of existing action. |
| **`access_right`** | `create` only | `model_name` | Creates/updates model ACL (`ir.model.access`). |
| **`record_rule`** | `create` only | `model_name` | Creates/updates security domain filter (`ir.rule`). |
| **`menu`** | `create` only | `model_name` | Creates menu and associated window action. |

> [!CAUTION]
> **STRICT CONSTRAINT:** Setting `action='update'` on `model`, `field`, `menu`, `access_right`, or `record_rule` will raise an immediate Odoo `ValidationError`. Update detection for these types is handled automatically by the planner at runtime.

---

## 3. Step Specification by Object Type (`meta.migration.step`)

### 3.1. Model Step (`object_type = 'model'`)
- **Action:** Must be `'create'`.
- **Required Fields:**
  - `model_name` *(Char)*: Technical name (e.g., `'x_warranty_claim'` or existing `'sale.order'`).
- **Optional Setup Fields:**
  - `model_description` *(Char)*: Display name/label (e.g., `'Warranty Claim'`).
  - `target_model_name` *(Char)*: Rename model on target system (leave blank to keep `model_name`).
  - `transient` *(Boolean)*: `True` if `models.TransientModel` (wizard), `False` for standard `models.Model` (default `False`).
  - **Auto-create Flags (Booleans):**
    - `create_list_view`: Auto-generate list/tree view on target (default `True`).
    - `create_form_view`: Auto-generate form view on target (default `True`).
    - `create_search_view`: Auto-generate search view on target (default `True`).
    - `create_menu`: Auto-generate menu item under custom menus (default `True`).
    - `copy_access_rights`: Copy model access rights (default `True`).
    - `copy_record_rules`: Copy record rules (default `False`).

---

### 3.2. Field Step (`object_type = 'field'`)
- **Action:** Must be `'create'`.
- **Required Fields:**
  - `model_name` *(Char)*: Model containing the field (e.g., `'x_warranty_claim'`).
  - `field_name` *(Char)*: Technical field name (e.g., `'x_serial_no'`). *Empty string means migrate all manual fields of the model.*
- **Core Field Properties:**
  - `field_description` *(Char)*: Field label displayed in UI.
  - `ttype` *(Selection)*: Field type:
    `'char'`, `'integer'`, `'float'`, `'monetary'`, `'boolean'`, `'text'`, `'html'`, `'date'`, `'datetime'`, `'binary'`, `'selection'`, `'many2one'`, `'one2many'`, `'many2many'`.
  - `help` *(Text)*: **Located in Field Definition group.** Tooltip text displayed to users.
- **Relational & Selection Fields (Conditional Requirements):**
  - If `ttype in ('many2one', 'one2many', 'many2many')`:
    - `relation` *(Char, Required)*: Comodel technical name (e.g., `'res.partner'`).
  - If `ttype == 'one2many'`:
    - `relation_field` *(Char, Required)*: Inverse field on comodel (e.g., `'claim_id'`).
  - If `ttype == 'many2one'`:
    - `on_delete` *(Selection)*: `'set null'` (default), `'cascade'`, `'restrict'`.
  - If `ttype == 'selection'`:
    - `selection` *(Text, Required)*: Python list of string tuples, e.g. `"[('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')]"`
- **ORM Storage & Flags:**
  - `required` *(Boolean)*: Default `False`.
  - `readonly` *(Boolean)*: Default `False`.
  - `store` *(Boolean)*: Default `True`.
  - `index` *(Boolean)*: Default `False`.
  - `copied` *(Boolean)*: Default `True`.
  - `translate` *(Boolean)*: Default `False` (valid for `char`, `text`, `html`).

#### Strict Rules for Computed vs. Related Fields:
> [!IMPORTANT]
> 1. **Compute & Depends Mutual Requirement:**
>    - If `compute` is set $\rightarrow$ `depends` is **MANDATORY**.
>    - If `depends` is set $\rightarrow$ `compute` is **MANDATORY**.
> 2. **Related Mutual Exclusion:**
>    - If `related` is set $\rightarrow$ `compute` and `depends` **MUST BE EMPTY / FALSE**.
>    - If `compute` or `depends` is set $\rightarrow$ `related` **MUST BE EMPTY / FALSE**.
> 3. **Syntax:**
>    - `compute`: Multi-line Python snippet, e.g.:
>      ```python
>      for rec in self:
>          rec.x_total_days = (rec.date_end - rec.date_start).days if rec.date_end and rec.date_start else 0
>      ```
>    - `depends`: Comma-separated dependencies, e.g. `'date_start,date_end'`
>    - `related`: Dot-notated path, e.g. `'partner_id.phone'`

---

### 3.3. View Step (`object_type = 'view'`)
- **Actions:** `'create'` OR `'update'`.
- **Case A: `action = 'create'` (New View):**
  - `model_name` *(Char, Required)*: e.g. `'x_warranty_claim'`.
  - `view_type` *(Selection, Required)*: `'list'`, `'form'`, `'search'`, `'kanban'`, `'qweb'`.
  - `view_name` *(Char, Optional)*: e.g. `'x_warranty_claim.form'`.
  - `priority` *(Integer, Optional)*: Sequence priority (default `16`).
  - `arch` *(Text, Optional)*: XML definition string, e.g.:
    ```xml
    <form string="Warranty Claim">
        <header>
            <field name="x_status" widget="statusbar"/>
        </header>
        <sheet>
            <group>
                <field name="x_name"/>
                <field name="x_partner_id"/>
            </group>
        </sheet>
    </form>
    ```
- **Case B: `action = 'update'` (Extension / Inheritance):**
  - `xml_id` *(Char, Required)*: Target view external ID with module prefix, e.g. `'sale.view_order_form'`.
  - `inherit_xml_id` *(Char, Optional)*: Base view to inherit from.
  - `mode` *(Selection)*: `'extension'` (default for updates) or `'primary'`.
  - `arch` *(Text, Required)*: XPath modification snippet, e.g.:
    ```xml
    <xpath expr="//field[@name='payment_term_id']" position="after">
        <field name="x_claim_reference"/>
    </xpath>
    ```

---

### 3.4. Server Action Step (`object_type = 'server_action'`)
- **Actions:** `'create'` OR `'update'`.
- **Required Fields:**
  - `xml_id` *(Char, Required)*: Must use `'module.name'` format, e.g. `'x_warranty.action_approve_claim'`.
- **Setup Fields:**
  - `action_name` *(Char)*: Label displayed in Action dropdown, e.g. `'Approve Claim'`.
  - `model_name` *(Char)*: Technical target model, e.g. `'x_warranty_claim'`.
  - `state` *(Selection)*: `'code'` (default), `'object_create'`, `'object_write'`, `'multi'`.
  - `code` *(Text)*: Python logic executed in server context (`record`, `records`, `env`):
    ```python
    for record in records:
        if record.x_status == 'draft':
            record.write({'x_status': 'approved'})
    ```
  - `binding_model` *(Char, Optional)*: Model where button/action appears.
  - `binding_type` *(Selection)*: `'action'` (Action menu button) or `'report'`.

---

### 3.5. Access Right Step (`object_type = 'access_right'`)
- **Action:** Must be `'create'`.
- **Required Fields:**
  - `model_name` *(Char, Required)*: Model being secured, e.g. `'x_warranty_claim'`.
- **Setup Fields:**
  - `access_name` *(Char)*: Identifier, e.g. `'access_x_warranty_claim_user'`.
  - `group_xml_id` *(Char)*: Target security group external ID (e.g. `'base.group_user'`). *Leave empty to apply to all internal users.*
  - `perm_read` *(Boolean)*: Default `True`.
  - `perm_write` *(Boolean)*: Default `False`.
  - `perm_create` *(Boolean)*: Default `False`.
  - `perm_unlink` *(Boolean)*: Default `False`.

---

### 3.6. Record Rule Step (`object_type = 'record_rule'`)
- **Action:** Must be `'create'`.
- **Required Fields:**
  - `model_name` *(Char, Required)*: Model being restricted, e.g. `'x_warranty_claim'`.
- **Setup Fields:**
  - `rule_name` *(Char)*: Rule label, e.g. `'Warranty Multi-Company Rule'`.
  - `domain_force` *(Text)*: Odoo domain string filter, e.g.:
    `"['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]"`
  - `group_xml_id` *(Char, Optional)*: Group XML ID (empty = global rule).
  - `rule_active` *(Boolean)*: Default `True`.

---

### 3.7. Menu Step (`object_type = 'menu'`)
- **Action:** Must be `'create'`.
- **Required Fields:**
  - `model_name` *(Char, Required)*: Model to open via window action.
- **Setup Fields:**
  - `menu_name` *(Char)*: Label displayed in sidebar/topbar.
  - `parent_xml_id` *(Char, Optional)*: Parent menu item external ID (e.g. `'base.menu_custom'`).
  - `menu_sequence` *(Integer)*: Ordering index (default `10`).

---

## 4. The Dependency Sequence Law

When constructing a migration job with multiple steps, assign `sequence` numbers following this strict dependency order:

```mermaid
flowchart TD
    S10["1. Model Step (seq: 10)"] --> S20["2. Basic Fields (Char, Int, Float, Date, Selection) (seq: 20-40)"]
    S20 --> S50["3. Many2one Relational Fields (seq: 50)"]
    S50 --> S60["4. One2many Inverses (seq: 60)"]
    S60 --> S70["5. Computed & Related Fields (seq: 70)"]
    S70 --> S80["6. Views (Create Form/List & Update XPaths) (seq: 80-90)"]
    S80 --> S100["7. Server Actions (seq: 100)"]
    S100 --> S110["8. Access Rights (ACL) & Record Rules (seq: 110-120)"]
    S110 --> S130["9. Navigation Menus (seq: 130)"]
```

> [!TIP]
> Spacing sequence numbers by `10` allows injecting intermediate steps later without renumbering the whole batch.

---

## 5. Direct Python Creation Recipe (Copy-Paste Ready)

When an AI agent needs to programmatically generate a complete, valid migration scenario via Python script or ORM execution, use this pattern:

```python
from odoo.fields import Command
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID
import odoo

odoo.tools.config.parse_config(['-c', '/opt/odoo19.conf', '-d', 'odoo19'])

with Registry('odoo19').cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Resolve or create Connections
    conn = env['meta.migration.connection'].search([], limit=1)
    if not conn:
        conn = env['meta.migration.connection'].create({
            'name': 'Local Staging',
            'url': 'http://localhost:8019',
            'db': 'odoo19',  # NOTE: field is 'db', NEVER 'database'
            'username': 'admin',
            'password': 'admin',
        })

    # 2. Create Job with ordered Steps in one atomic call
    job = env['meta.migration.job'].create({
        'name': 'Warranty Management Customization',
        'source_connection_id': conn.id,
        'target_connection_id': conn.id,
        'on_conflict': 'overwrite',
        'stop_on_error': True,
        'step_ids': [
            # Step 1: Model
            Command.create({
                'sequence': 10,
                'object_type': 'model',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'model_description': 'Warranty Claim',
                'create_list_view': True,
                'create_form_view': True,
                'create_menu': True,
            }),
            # Step 2: Char Field with Help Tooltip
            Command.create({
                'sequence': 20,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'field_name': 'x_serial_no',
                'field_description': 'Device Serial Number',
                'ttype': 'char',
                'required': True,
                'index': True,
                'help': 'Unique manufacturer hardware serial number.',
            }),
            # Step 3: Selection Field
            Command.create({
                'sequence': 30,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'field_name': 'x_status',
                'field_description': 'Claim Status',
                'ttype': 'selection',
                'selection': "[('draft', 'Draft'), ('in_review', 'In Review'), ('resolved', 'Resolved')]",
                'help': 'Current workflow phase.',
            }),
            # Step 4: Many2one Field
            Command.create({
                'sequence': 40,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'field_name': 'x_customer_id',
                'field_description': 'Customer',
                'ttype': 'many2one',
                'relation': 'res.partner',
                'on_delete': 'set null',
            }),
            # Step 5: Computed Field (Requires depends)
            Command.create({
                'sequence': 50,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'field_name': 'x_claim_code',
                'field_description': 'Formatted Claim Code',
                'ttype': 'char',
                'compute': "for rec in self:\n    rec.x_claim_code = f'CLM-{rec.x_serial_no or \"000\"}'\n",
                'depends': 'x_serial_no',
                'store': True,
            }),
            # Step 6: Related Field (No compute, no depends)
            Command.create({
                'sequence': 60,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'field_name': 'x_customer_email',
                'field_description': 'Customer Email',
                'ttype': 'char',
                'related': 'x_customer_id.email',
                'readonly': True,
            }),
            # Step 7: Form View
            Command.create({
                'sequence': 70,
                'object_type': 'view',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'view_name': 'x_warranty_claim.form',
                'view_type': 'form',
                'arch': '<form string="Warranty Claim"><sheet><group><field name="x_serial_no"/><field name="x_customer_id"/></group></sheet></form>',
            }),
            # Step 8: View Update (XPath extension)
            Command.create({
                'sequence': 80,
                'object_type': 'view',
                'action': 'update',
                'model_name': 'sale.order',
                'xml_id': 'sale.view_order_form',
                'arch': '<xpath expr="//field[@name=\'payment_term_id\']" position="after"><field name="x_warranty_ref"/></xpath>',
            }),
            # Step 9: Server Action
            Command.create({
                'sequence': 90,
                'object_type': 'server_action',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'action_name': 'Resolve Claim',
                'xml_id': 'x_warranty.action_resolve_claim',
                'state': 'code',
                'code': "records.filtered(lambda r: r.x_status != 'resolved').write({'x_status': 'resolved'})\n",
            }),
            # Step 10: Access Right
            Command.create({
                'sequence': 100,
                'object_type': 'access_right',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'access_name': 'access_x_warranty_claim_user',
                'group_xml_id': 'base.group_user',
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': False,
            }),
            # Step 11: Menu Item
            Command.create({
                'sequence': 110,
                'object_type': 'menu',
                'action': 'create',
                'model_name': 'x_warranty_claim',
                'menu_name': 'Warranty Claims',
                'parent_xml_id': 'base.menu_custom',
            }),
        ]
    })

    cr.commit()
    print(f"Migration Job {job.id} created successfully with {len(job.step_ids)} steps.")
```

---

## 6. Seeding Mock Runs & Visual Diffs (`meta.migration.change`)

When an AI needs to populate a visual Diff demo for user verification without waiting for XML-RPC execution:

```python
import json

run = env['meta.migration.run'].create({
    'job_id': job.id,
    'source_connection_id': job.source_connection_id.id,
    'target_connection_id': job.target_connection_id.id,
    'mode': 'test',
    'state': 'done',
    'summary_text': 'All changes analyzed and ready for review',
})

# Example 1: Field Update Diff (Shows yellow badge, changed attribute chips)
env['meta.migration.change'].create({
    'run_id': run.id,
    'object_type': 'field',
    'change_type': 'update',
    'status': 'planned',
    'name': 'field x_warranty_claim.x_serial_no',
    'target_ref': 'x_warranty_claim.x_serial_no',
    'old_raw': json.dumps({'name': 'x_serial_no', 'required': False, 'index': False}),
    'new_raw': json.dumps({'name': 'x_serial_no', 'required': True, 'index': True}),
    'message': 'Modified attributes: required, index.',
})

# Example 2: View Update CodeDiff (Shows side-by-side green/red XML diff)
env['meta.migration.change'].create({
    'run_id': run.id,
    'object_type': 'view',
    'change_type': 'update',
    'status': 'planned',
    'name': 'update view sale.view_order_form',
    'target_ref': 'sale.view_order_form',
    'old_raw': '<form><sheet><field name="payment_term_id"/></sheet></form>',
    'new_raw': '<form><sheet><field name="payment_term_id"/><field name="x_warranty_ref"/></sheet></form>',
    'extra_raw': json.dumps({
        'added': ['<field name="x_warranty_ref"/>'],
        'present': ['<field name="payment_term_id"/>'],
    }),
    'message': 'Appended 1 field element into sale.order form.',
})
```

---

## 7. Critical Pitfalls & Anti-Patterns (The 8 Sins)

1. **NEVER use relational IDs to local models:** Do not use `model_id = fields.Many2one('ir.model')` or `Many2one('ir.ui.view')`. Steps define portable data blueprints for remote targets, not local records.
2. **NEVER set `action='update'` on `model` or `field`:** The step action must be `'create'`. Update detection occurs dynamically during planning.
3. **NEVER omit module prefix in `xml_id`:** Always use `'module.record_id'` (e.g., `'sale.view_order_form'`). A missing dot will trigger a `ValidationError`.
4. **NEVER mix `related` with `compute` or `depends`:** They are mutually exclusive.
5. **NEVER set `compute` without `depends` (or vice-versa):** Always provide both together.
6. **NEVER use `database` in `meta.migration.connection`:** The field name is `db`, not `database`.
7. **NEVER forget `source_connection_id` when creating `meta.migration.run`:** It is a `NOT NULL` database column.
8. **NEVER create ad-hoc test scripts outside `scripts/run_test.py`:** Keep all temporary validation logic clean and tear down test records.
