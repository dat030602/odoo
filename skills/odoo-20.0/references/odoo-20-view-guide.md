# Odoo 20 View Guide

## Coding Conventions

- Use model-first IDs, e.g. `my_model_view_list` and `my_model_view_form`.
- Always use `<list>` (never `<tree>`).
- Always use direct modifier expressions: `invisible="state == 'done'"`, `readonly="not is_editable"`. Never use legacy `attrs="..."`.
- In `<search>` views, do not use `start_month`, `end_month`, `start_year`, or `end_year` on date filters.
- In QWeb templates, use `<t t-out="..."/>` (never `t-esc`) and parametric `t-call` attributes.

---

## Table of Contents

- [View Types](#view-types)
- [List Views](#list-views)
- [Form Views](#form-views)
- [Search Views & Date Filters](#search-views--date-filters)
- [Kanban Views](#kanban-views)
- [View Inheritance & XPath](#view-inheritance--xpath)

---

## View Types

| Type | Root Tag | Description |
|------|----------|-------------|
| **List** | `<list>` | Tabular record listing |
| **Form** | `<form>` | Detailed single-record editor |
| **Search** | `<search>` | Filters and search facets |
| **Kanban** | `<kanban>` | Visual cards / Kanban board |
| **Calendar** | `<calendar>` | Scheduled appointments / dates |
| **Graph** | `<graph>` | Bar, line, and pie charts |
| **Pivot** | `<pivot>` | Multi-dimensional pivot tables |
| **Activity** | `<activity>` | Schedule and track next activities |

---

## List Views

```xml
<record id="project_task_view_list" model="ir.ui.view">
    <field name="name">project.task.list</field>
    <field name="model">project.task</field>
    <field name="arch" type="xml">
        <list string="Tasks" multi_edit="1" sample="1">
            <field name="sequence" widget="handle"/>
            <field name="name"/>
            <field name="user_id" widget="many2one_avatar_user"/>
            <field name="date_deadline" widget="remaining_days"/>
            <field name="tag_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
            <field name="state" widget="badge"
                   decoration-info="state == 'draft'"
                   decoration-warning="state == 'in_progress'"
                   decoration-success="state == 'done'"/>
        </list>
    </field>
</record>
```

---

## Form Views

```xml
<record id="project_task_view_form" model="ir.ui.view">
    <field name="name">project.task.form</field>
    <field name="model">project.task</field>
    <field name="arch" type="xml">
        <form string="Task">
            <header>
                <button name="action_start" type="object" string="Start Task"
                        class="btn-primary" invisible="state != 'draft'"/>
                <button name="action_done" type="object" string="Complete"
                        class="btn-success" invisible="state != 'in_progress'"/>
                <field name="state" widget="statusbar" statusbar_visible="draft,in_progress,done"/>
            </header>
            <sheet>
                <div class="oe_title">
                    <h1>
                        <field name="name" placeholder="Task Title..." readonly="state == 'done'"/>
                    </h1>
                </div>
                <group>
                    <group>
                        <field name="user_id" widget="many2one_avatar_user"/>
                        <field name="company_id" groups="base.group_multi_company"/>
                    </group>
                    <group>
                        <field name="date_deadline"/>
                        <field name="tag_ids" widget="many2many_tags"/>
                    </group>
                </group>
                <notebook>
                    <page string="Description" name="description">
                        <field name="description" placeholder="Add detailed notes..."/>
                    </page>
                </notebook>
            </sheet>
            <chatter/>
        </form>
    </field>
</record>
```

---

## Search Views & Date Filters

> **Odoo 20 Change**: Date filters do NOT take range attributes (`start_month`, `end_month`, `start_year`, `end_year`). These are handled dynamically by the search bar.

```xml
<record id="project_task_view_search" model="ir.ui.view">
    <field name="name">project.task.search</field>
    <field name="model">project.task</field>
    <field name="arch" type="xml">
        <search string="Tasks">
            <!-- Search fields -->
            <field name="name" string="Task"/>
            <field name="user_id"/>
            <field name="tag_ids"/>

            <!-- Filters -->
            <filter name="my_tasks" string="My Tasks" domain="[('user_id', '=', uid)]"/>
            <filter name="open_tasks" string="Open" domain="[('state', 'in', ('draft', 'in_progress'))]"/>
            <separator/>

            <!-- Clean Odoo 20 date filter (no start_month/end_month) -->
            <filter name="date_deadline" string="Deadline" date="date_deadline"/>

            <!-- Group by -->
            <group expand="0" string="Group By">
                <filter name="group_user" string="Assignee" context="{'group_by': 'user_id'}"/>
                <filter name="group_state" string="Status" context="{'group_by': 'state'}"/>
            </group>
        </search>
    </field>
</record>
```

---

## Kanban Views

```xml
<record id="project_task_view_kanban" model="ir.ui.view">
    <field name="name">project.task.kanban</field>
    <field name="model">project.task</field>
    <field name="arch" type="xml">
        <kanban default_group_by="state" sample="1">
            <templates>
                <t t-name="card">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="o_kanban_record_title" t-out="record.name.value"/>
                    </div>
                    <div class="text-muted small mb-2">
                        <span t-out="record.date_deadline.value"/>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <field name="tag_ids" widget="many2many_tags"/>
                        <field name="user_id" widget="many2one_avatar_user"/>
                    </div>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

---

## View Inheritance & XPath

Always target unique elements or use precise XPaths:

```xml
<record id="project_task_view_form_inherit" model="ir.ui.view">
    <field name="name">project.task.form.inherit</field>
    <field name="model">project.task</field>
    <field name="inherit_id" ref="project.project_task_view_form"/>
    <field name="arch" type="xml">
        <!-- Add field after deadline -->
        <xpath expr="//field[@name='date_deadline']" position="after">
            <field name="priority" widget="priority"/>
        </xpath>

        <!-- Modify existing field attributes -->
        <xpath expr="//field[@name='user_id']" position="attributes">
            <attribute name="required">1</attribute>
        </xpath>
    </field>
</record>
```

