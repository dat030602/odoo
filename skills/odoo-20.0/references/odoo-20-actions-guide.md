# Odoo 20 Actions & Menus Guide

## Coding Conventions

- Name action IDs `action_<model>_<view_type>` or `action_<model>`.
- Use `<list>` in `view_mode` string: `view_mode="list,form"`.
- In scheduled actions (crons) handling large batches, use `self.env['ir.cron']._commit_progress()` to commit progress and respect cron execution time limits.
- Bind contextual actions using `binding_model_id` and `binding_view_types`.

---

## Table of Contents

- [Action Types Overview](#action-types-overview)
- [Window Actions (`ir.actions.act_window`)](#window-actions-iractionsact_window)
- [Menu Items (`<menuitem>`)](#menu-items-menuitem)
- [Server Actions (`ir.actions.server`)](#server-actions-iractionsserver)
- [Scheduled Actions (`ir.cron`)](#scheduled-actions-ircron)
- [URL & Client Actions](#url--client-actions)

---

## Action Types Overview

| Model | Purpose |
|-------|---------|
| `ir.actions.act_window` | Opens views for a model (list, form, kanban) |
| `ir.actions.server` | Runs Python code or automated workflows |
| `ir.actions.report` | Generates and downloads PDF/HTML reports |
| `ir.actions.client` | Launches an OWL client action / full-screen UI |
| `ir.actions.act_url` | Redirects the user browser to a URL |

---

## Window Actions (`ir.actions.act_window`)

```xml
<record id="action_project_task" model="ir.actions.act_window">
    <field name="name">Tasks</field>
    <field name="res_model">project.task</field>
    <field name="view_mode">list,form,kanban,calendar</field>
    <field name="search_view_id" ref="project_task_view_search"/>
    <field name="domain">[('state', '!=', 'cancel')]</field>
    <field name="context">{'search_default_open_tasks': 1}</field>
    <field name="help" type="html">
        <p class="o_view_nocontent_smiling_face">
            Create your first project task!
        </p>
    </field>
</record>
```

---

## Menu Items (`<menuitem>`)

Structure menus cleanly from root to sub-menus:

```xml
<!-- Root Application Menu -->
<menuitem id="menu_project_root"
          name="Projects"
          web_icon="project,static/description/icon.png"
          sequence="50"/>

<!-- Category Menu -->
<menuitem id="menu_project_tasks_category"
          name="Tasks"
          parent="menu_project_root"
          sequence="10"/>

<!-- Action Menu Item -->
<menuitem id="menu_project_task_all"
          name="All Tasks"
          parent="menu_project_tasks_category"
          action="action_project_task"
          sequence="10"/>
```

---

## Server Actions (`ir.actions.server`)

Server actions can run Python code and bind to the Action menu of list or form views:

```xml
<record id="action_server_mark_tasks_done" model="ir.actions.server">
    <field name="name">Mark as Completed</field>
    <field name="model_id" ref="model_project_task"/>
    <field name="binding_model_id" ref="model_project_task"/>
    <field name="binding_view_types">list,form</field>
    <field name="state">code</field>
    <field name="code">
records.action_done()
    </field>
</record>
```

---

## Scheduled Actions (`ir.cron`)

Cron jobs run periodic background tasks:

```xml
<record id="cron_cleanup_abandoned_tasks" model="ir.cron">
    <field name="name">Project: Cleanup Abandoned Draft Tasks</field>
    <field name="model_id" ref="model_project_task"/>
    <field name="state">code</field>
    <field name="code">model._cron_cleanup_abandoned()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="active">True</field>
</record>
```

### Implementing Batch Processing in Cron Methods

In Python, handle large batches with `_commit_progress()`:

```python
class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.model
    def _cron_cleanup_abandoned(self):
        abandoned_tasks = self.search([
            ('state', '=', 'draft'),
            ('create_date', '<=', 'today -30d'),
        ])
        for task in abandoned_tasks:
            task.action_archive()
            # Commit and check remaining cron execution time
            time_left = self.env['ir.cron']._commit_progress()
            if time_left == 0:
                _logger.info("Cron time limit reached, yielding remaining tasks to next run")
                break
```

