# Odoo 20 Development Guide

Comprehensive end-to-end guide for creating and structuring Odoo 20 modules.

## Table of Contents

- [Module Architecture](#module-architecture)
- [Module Directory Layout](#module-directory-layout)
- [Creating a New Module Step-by-Step](#creating-a-new-module-step-by-step)
- [Wizards & Transient Models](#wizards--transient-models)
- [Web Assets & OWL 3 Frontend](#web-assets--owl-3-frontend)
- [Development Workflow](#development-workflow)

---

## Module Architecture

Odoo 20 modules follow a clean separation of concerns:
- **`models/`**: Business models, logic, fields, compute methods.
- **`security/`**: User groups and access rules in `ir.access.csv`.
- **`views/`**: XML views (`<list>`, `<form>`, `<search>`, `<kanban>`) and menu structures.
- **`data/`**: Initial configuration data, sequences, crons, email templates.
- **`report/`**: QWeb reports and print actions.
- **`static/`**: OWL 3 components, JavaScript, SCSS, icons.
- **`tests/`**: Unit tests (`TransactionCase` and `@odoo/hoot`).

---

## Module Directory Layout

```
my_module/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── data/
│   └── sequence_data.xml
├── models/
│   ├── __init__.py
│   ├── project_task.py
│   └── project_category.py
├── report/
│   ├── task_report.py
│   └── task_report_views.xml
├── security/
│   ├── my_module_groups.xml
│   └── ir.access.csv
├── static/
│   ├── description/
│   │   └── icon.png
│   ├── src/
│   │   ├── components/
│   │   │   ├── task_card/
│   │   │   │   ├── task_card.js
│   │   │   │   └── task_card.xml
│   │   │   └── ...
│   │   └── scss/
│   │       └── style.scss
│   └── tests/
│       └── task_card.test.js
├── tests/
│   ├── __init__.py
│   └── test_task.py
├── views/
│   ├── project_task_views.xml
│   └── menus.xml
└── wizard/
    ├── __init__.py
    ├── task_batch_assign.py
    └── task_batch_assign_views.xml
```

---

## Creating a New Module Step-by-Step

### 1. Root `__init__.py`
```python
from . import controllers
from . import models
from . import wizard
```

### 2. Manifest `__manifest__.py`
```python
{
    'name': "Task Management",
    'version': '20.0.1.0.0',
    'summary': "Manage tasks, team allocations, and deadlines",
    'author': "My Company",
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/my_module_groups.xml',
        'security/ir.access.csv',
        'data/sequence_data.xml',
        'views/project_task_views.xml',
        'wizard/task_batch_assign_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'my_module/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'my_module/static/tests/**/*.test.js',
        ],
    },
    'installable': True,
    'application': True,
}
```

### 3. Security `security/ir.access.csv`
```csv
id,name,model_id,group_id/id,operation,domain
access_project_task_user,project.task.user,project.task,base.group_user,cru,
access_project_task_manager,project.task.manager,project.task,base.group_system,crud,
project_task_comp_rule,Project Task Multi-Company,project.task,,crud,"[('company_id', 'in', company_ids)]"
```

### 4. Business Model `models/project_task.py`
```python
from odoo import api, fields, models

class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Task'
    _rec_names_search = ('name', 'code')

    name = fields.Char(string="Title", required=True, tracking=True)
    code = fields.Char(string="Reference", copy=False)
    user_id = fields.Many2one('res.users', string="Assignee", tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], default='draft', tracking=True)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})
```

---

## Wizards & Transient Models

Wizards provide interactive multi-step popups and batch tools using `models.TransientModel`:

### Wizard Model `wizard/task_batch_assign.py`
```python
from odoo import fields, models

class TaskBatchAssign(models.TransientModel):
    _name = 'task.batch.assign.wizard'
    _description = 'Batch Assign Tasks'

    user_id = fields.Many2one('res.users', string="New Assignee", required=True)

    def action_apply(self):
        active_ids = self.env.context.get('active_ids', [])
        tasks = self.env['project.task'].browse(active_ids)
        tasks.write({'user_id': self.user_id.id})
        return {'type': 'ir.actions.act_window_close'}
```

### Wizard View `wizard/task_batch_assign_views.xml`
```xml
<record id="task_batch_assign_view_form" model="ir.ui.view">
    <field name="name">task.batch.assign.form</field>
    <field name="model">task.batch.assign.wizard</field>
    <field name="arch" type="xml">
        <form string="Batch Assign Assignee">
            <group>
                <field name="user_id"/>
            </group>
            <footer>
                <button name="action_apply" string="Assign" type="object" class="btn-primary"/>
                <button string="Cancel" class="btn-secondary" special="cancel"/>
            </footer>
        </form>
    </field>
</record>
```

---

## Web Assets & OWL 3 Frontend

Build modern OWL 3 components using `useProps` and `proxy`:

```javascript
import { Component, proxy, t, useProps } from "@odoo/owl";

export class TaskBadge extends Component {
    static template = "my_module.TaskBadge";
    props = useProps({
        status: t.string(),
    });
}
```

---

## Development Workflow

1. Start Odoo 20 server pointing to your addons path:
   ```bash
   python3 odoo-bin -c odoo.conf -u my_module --dev=all
   ```
2. Verify all models and views load without tracebacks or deprecation warnings.
3. Run automated tests:
   ```bash
   python3 odoo-bin -c odoo.conf -d test_db --test-enable --stop-after-init -u my_module
   ```

