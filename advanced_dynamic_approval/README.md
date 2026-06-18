# Dynamic Approval Workflow Builder for Odoo

Advanced extension module for Odoo that extends the default approval system and provides configurable approval workflows for any Odoo model.

The module allows administrators to create approval flows visually, define Python-based conditional execution, generate isolated views dynamically, create approval menus automatically, and manage approval history without modifying original Odoo views.

---

# Objective

Provide a reusable approval engine for any model in Odoo while reusing the existing approval framework.

Main goals:

* Reuse Odoo core approval system
* Support approval workflow for any model
* Multi-stage approval process
* Python-based condition execution
* Dynamic menu generation
* Dynamic list/form view generation
* Separate approval interface from original views
* Keep original business views untouched
* Approval history tracking
* Permission-based approval actions

---

# Core Design Principles

Architecture philosophy:

* Extend Odoo approval core instead of replacing it
* Never modify original business views
* Never use xpath inheritance on original views
* Generate isolated approval views
* Generate independent approval menus
* Reuse approval.request when possible

Must NOT:

* Override core approval logic deeply
* Modify standard Odoo business forms
* Break default workflow behavior

---

# Business Flow

Example workflow.

Sales Order Approval

Draft

↓

Manager Approval

↓

Condition Check

Python code executes

↓

result == True ?

YES → Director Approval

NO → Finance Approval

↓

Approved

Each stage has independent:

* Menu
* List View
* Form View
* Domain Filtering

---

# System Architecture

approval.workflow.config

↓

approval.workflow.stage

↓

approval.workflow.edge

↓

approval.workflow.condition

↓

approval.field.config

↓

approval.domain.config

↓

approval.view.generator

↓

Create Views

Create Actions

Create Menus

↓

approval.request (core reuse)

↓

approval.history.log

---

# Model Design

## 1. approval.workflow.config

Main workflow configuration.

Purpose:

Store workflow settings for target model.

Fields:

| Field                | Type               |
| -------------------- | ------------------ |
| name                 | Char               |
| model_id             | Many2one(ir.model) |
| approval_category_id | Many2one           |
| active               | Boolean            |

Example:

* Sales Order Approval
* Purchase Order Approval
* Expense Approval

One workflow per business process.

---

## 2. approval.workflow.stage

Approval stages.

Purpose:

Defines approval sequence.

Fields:

| Field          | Type      |
| -------------- | --------- |
| workflow_id    | Many2one  |
| name           | Char      |
| sequence       | Integer   |
| approver_type  | Selection |
| user_id        | Many2one  |
| group_id       | Many2one  |
| custom_view_id | Many2one  |
| menu_id        | Many2one  |
| action_id      | Many2one  |
| pos_x          | Integer   |
| pos_y          | Integer   |

Approver types:

* fixed_user
* group
* manager
* dynamic_field

Example:

* Manager Approval
* Finance Approval
* Director Approval

---

## 3. approval.workflow.edge

Stores workflow connections.

Purpose:

Connect drag/drop workflow nodes.

Fields:

| Field           | Type      |
| --------------- | --------- |
| source_stage_id | Many2one  |
| target_stage_id | Many2one  |
| edge_type       | Selection |

edge_type values:

* normal
* true
* false

Example:

Manager Approval

↓

Condition Node

↓

True → Director

False → Finance

---

## 4. approval.workflow.condition

Conditional execution logic.

Purpose:

Execute Python code and route workflow.

Fields:

| Field             | Type     |
| ----------------- | -------- |
| stage_id          | Many2one |
| python_expression | Text     |

Administrator writes Python code.

Example.

```python
if self.amount_total > 10000:
    result = True
else:
    result = False
```

Code must assign:

```python
result = True
```

or

```python
result = False
```

---

# Python Execution Engine

Code executes using eval context.

Context variables available.

```python
def _get_python_eval_context(self):

    self.ensure_one()

    def _dynamic_import(mod):
        modules_list = sys.modules
        if mod in modules_list:
            return sys.modules[mod]
        __import__(mod)
        return sys.modules[mod]

    return {
        '_dynamic_import': _dynamic_import,
        'mb': {
            're': re,
            'json': json,
            'random': random,
            'io': io,
            'hashlib': hashlib,
            'hmac': hmac,
            'urllib': urllib,
            'ast': ast,
            'requests': requests,
            'base64': base64,
            'xmlrpc.client': xmlrpc.client,
            'http.client': http.client,
            'socket': socket,
        },
        'env': self.env,
        'user': self.env.user,
        'self': record,
        'result': None,
    }
```

---

# Record Binding

Current business record must be injected as:

```python
self
```

Example.

If approval belongs to sale.order.

```python
self == sale.order current record
```

Sample code.

```python
if self.amount_total > 5000:
    result = True
else:
    result = False
```

Execution.

```python
localdict = self._get_python_eval_context()

safe_eval(
    python_expression,
    localdict,
    mode='exec'
)

result = localdict.get("result")
```

---

## 5. approval.domain.config

Purpose:

Allow administrator to choose fields for filtering stage menus.

Fields:

| Field       | Type                      |
| ----------- | ------------------------- |
| workflow_id | Many2one                  |
| field_id    | Many2one(ir.model.fields) |
| operator    | Selection                 |

Example.

Generate domain.

```python
[
  ('user_id','=',uid)
]
```

Supported fields from target model.

Example.

* user_id
* company_id
* salesperson_id
* state

---

## 6. approval.field.config

Purpose:

Choose fields used to generate views.

Fields:

| Field           | Type                      |
| --------------- | ------------------------- |
| workflow_id     | Many2one                  |
| field_id        | Many2one(ir.model.fields) |
| include_in_form | Boolean                   |
| include_in_tree | Boolean                   |

Admin selects visible fields.

---

## 7. approval.record.mapping

Purpose:

Map business document to approval workflow.

Fields:

| Field               | Type      |
| ------------------- | --------- |
| model_name          | Char      |
| res_id              | Integer   |
| workflow_id         | Many2one  |
| current_stage_id    | Many2one  |
| approval_request_id | Many2one  |
| state               | Selection |

States:

* draft
* waiting_approval
* approved
* rejected
* cancelled

---

## 8. approval.history.log

Audit history.

Fields:

| Field      | Type      |
| ---------- | --------- |
| model_name | Char      |
| res_id     | Integer   |
| stage_id   | Many2one  |
| action     | Selection |
| user_id    | Many2one  |
| comment    | Text      |
| datetime   | Datetime  |

Actions.

* approve
* reject
* cancel

---

# Visual Workflow Builder

Workflow created using drag/drop interface.

Frontend component.

Node graph builder.

Node types.

* approval
* condition
* end

Each stage stores position.

```python
pos_x = fields.Integer()
pos_y = fields.Integer()
```

Example.

Start

↓

Manager Approval

↓

Condition Node

↓

Director Approval

---

# Dynamic Menu Generation

Each stage generates separate menu.

Example.

Sales Approval

* Pending Manager Approval
* Pending Finance Approval
* Pending Director Approval

Created automatically.

Objects:

* ir.ui.menu
* ir.actions.act_window

---

# Domain Isolation

Each menu only displays records for that stage.

Manager menu.

```python
domain = [
   ('current_stage','=','manager')
]
```

Finance menu.

```python
domain = [
   ('current_stage','=','finance')
]
```

Director menu.

```python
domain = [
   ('current_stage','=','director')
]
```

Users never access wrong approval screen.

---

# Dynamic View Generation

No xpath inheritance.

No modification to original Odoo views.

System creates independent views.

Generated per stage.

Example.

For purchase.order.

Create:

* approval_purchase_manager_form
* approval_purchase_finance_form
* approval_purchase_director_form

---

# Form View Generation Rules

Views generated automatically.

Simple structure.

Rules:

* Group all standard fields inside group
* One2many and Many2many become notebook pages
* Footer contains approval buttons

Example.

```xml
<form>

    <sheet>

        <group>

            all simple fields

        </group>

        <notebook>

            relation fields pages

        </notebook>

    </sheet>

    <footer>

        Approve

        Reject

        Cancel

    </footer>

</form>
```

---

# One2Many and Many2Many Handling

If target model contains relational fields.

Example.

```python
order_line = one2many
tag_ids = many2many
```

System creates helper many2many fields.

Example.

```python
x_order_line_ids
```

Reason.

Odoo dynamic view generation handles direct relations more safely.

Rules.

Many2many and One2many displayed as notebook pages.

Example.

```xml
<notebook>

    <page string="Order Lines">

        <field name="x_order_line_ids"/>

    </page>

</notebook>
```

---

# Tree View Generation

Generate simple list automatically.

All selected fields added.

Example.

```xml
<tree>

    <field name="name"/>

    <field name="partner_id"/>

    <field name="amount_total"/>

    <field name="state"/>

</tree>
```

---

# Approval Actions

Each generated form contains custom footer buttons.

Never use default Odoo approval buttons.

Buttons:

* Approve
* Reject
* Cancel

Example.

```xml
<footer>

    <button
        name="action_custom_approve"
        string="Approve"
        type="object"/>

    <button
        name="action_custom_reject"
        string="Reject"
        type="object"/>

    <button
        name="action_custom_cancel"
        string="Cancel"
        type="object"/>

</footer>
```

---

# Approve Action

Method.

```python
action_custom_approve()
```

Flow.

User clicks Approve

↓

Create history

↓

Current stage has condition?

↓

Execute Python code

↓

Read variable result

↓

result == True ?

↓

Move to TRUE stage

Else move to FALSE stage

↓

If final stage

Mark approved

History.

```text
Action = approve
```

---

# Reject Action

Method.

```python
action_custom_reject()
```

Reject requires popup.

Popup fields.

| Field  | Type |
| ------ | ---- |
| reason | Text |

Popup.

Reject Approval

Reason

[________________]

Confirm

Reason required.

Flow.

User clicks Reject

↓

Open popup

↓

Enter reason

↓

Save history

↓

Mark rejected

↓

Notify creator

History.

```text
Action = reject
Comment = reject reason
```

---

# Reject Wizard

Model.

```python
approval.reject.wizard
```

Fields.

```python
reason = fields.Text(required=True)
```

Method.

```python
confirm_reject()
```

---

# Cancel Action

Method.

```python
action_custom_cancel()
```

Purpose.

Cancel approval process.

Final state.

```text
cancelled
```

---

# Cancel Permission Rules

Cancel button visible ONLY for:

* Document creator
* Manager

---

## Document Creator

Check.

```python
record.create_uid == env.user
```

---

## Manager

Group.

```python
approval.group_approval_manager
```

Check.

```python
env.user.has_group(
    "module.group_approval_manager"
)
```

---

# Cancel Button Visibility

Visible if.

```python
creator OR manager
```

Computed field.

```python
can_cancel = fields.Boolean(
    compute="_compute_can_cancel"
)
```

Example.

```python
def _compute_can_cancel(self):

    for rec in self:

        rec.can_cancel = (
            rec.create_uid == self.env.user
            or
            self.env.user.has_group(
                "module.group_approval_manager"
            )
        )
```

XML.

```xml
<button
    name="action_custom_cancel"
    string="Cancel"
    invisible="not can_cancel"/>
```

---

# Cancel Flow

User clicks Cancel

↓

Permission validation

↓

Create history

↓

Mark cancelled

↓

Stop workflow

History.

```text
Action = cancel
```

---

# Permission Matrix

| Action  | Creator | Approver | Manager |
| ------- | ------- | -------- | ------- |
| Approve | No      | Yes      | Yes     |
| Reject  | No      | Yes      | Yes     |
| Cancel  | Yes     | No       | Yes     |

---

# Notification Events

Approve.

Notify next approver.

Reject.

Notify creator with reason.

Cancel.

Notify all current approvers.

---

# Approval Engine

Main execution.

```python
def action_custom_approve():

    create_history()

    if current_stage.has_condition:

        result = evaluate_python()

        if result:
            next_stage = true_stage
        else:
            next_stage = false_stage

    else:

        next_stage = get_next_sequence()

    if next_stage:

        move_to_next_stage()

    else:

        complete_approval()
```

---

# Folder Structure

```text
dynamic_approval/

models/

    workflow_config.py
    workflow_stage.py
    workflow_edge.py
    workflow_condition.py
    field_config.py
    domain_config.py
    approval_mapping.py
    approval_history.py
    approval_engine.py
    view_generator.py

services/

    python_executor.py
    xml_generator.py
    menu_generator.py
    action_generator.py

wizard/

    reject_wizard.py

views/

    workflow_builder.xml
    workflow_config.xml
    approval_history.xml
    reject_wizard.xml

static/src/js/

    workflow_drag_drop.js

security/

    ir.model.access.csv
    security.xml
```

---

# Supported Versions

Compatible with:

* Odoo 17
* Odoo 18

---

# Final Architecture

Core Approval System (Reuse)

*

Workflow Builder

*

Python Execution Engine

*

Dynamic View Generator

*

Dynamic Menu Generator

*

Approval History Tracking

*

Permission-based Approval Actions

No modification to original Odoo views.
