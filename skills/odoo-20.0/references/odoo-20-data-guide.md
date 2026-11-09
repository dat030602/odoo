# Odoo 20 Data Guide

## Coding Conventions

- Store security access in `security/ir.access.csv`.
- In XML records for binary files, always use `type="bytes"` (never `type="base64"`).
- Use `noupdate="1"` on `<odoo>` or `<data>` for user-customizable initial records (sequences, categories).
- Use parametric `t-call` syntax `<t t-call="template_name" param="val"/>` in QWeb templates.

---

## Table of Contents

- [Data Files Overview](#data-files-overview)
- [XML Record Definition](#xml-record-definition)
- [Binary Files in XML (`type="bytes"`)](#binary-files-in-xml-typebytes)
- [CSV Data Files & `ir.access.csv`](#csv-data-files--iraccesscsv)
- [Evaluating Expressions with `eval`](#evaluating-expressions-with-eval)
- [Noupdate & Data Re-loading](#noupdate--data-re-loading)

---

## Data Files Overview

Odoo loads initial and demonstration data from XML and CSV files declared in `__manifest__.py`:

```python
'data': [
    'security/ir.access.csv',
    'data/sequence_data.xml',
    'data/mail_template_data.xml',
],
```

---

## XML Record Definition

### Basic Record

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="task_type_development" model="project.task.type">
        <field name="name">Development</field>
        <field name="sequence">10</field>
        <field name="fold">False</field>
    </record>
</odoo>
```

---

## Binary Files in XML (`type="bytes"`)

> **Odoo 20 Deprecation**: `type="base64"` on `<field file="..."/>` is deprecated in favor of **`type="bytes"`**.

To load binary attachments, images, or documents from module files:

```xml
<record id="sample_attachment_document" model="ir.attachment">
    <field name="name">Specification.pdf</field>
    <!-- Use type="bytes" in Odoo 20 -->
    <field name="datas" type="bytes" file="my_module/data/files/Specification.pdf"/>
    <field name="mimetype">application/pdf</field>
</record>
```

---

## CSV Data Files & `ir.access.csv`

In Odoo 20, all model access permissions and record rules are defined in CSV format:

File: `security/ir.access.csv`

```csv
id,name,model_id,group_id/id,operation,domain
access_project_task_user,project.task.user,project.task,project.group_project_user,cru,
access_project_task_manager,project.task.manager,project.task,project.group_project_manager,crud,
project_task_comp_rule,Project Task multi-company,project.task,,crud,"[('company_id', 'in', company_ids)]"
```

Rules:
- First column `id` is the XML ID.
- Second column `name` is the human-readable description.
- Third column `model_id` is the dotted model name (e.g. `project.task`).
- Fourth column `group_id/id` is the XML ID of the group (empty for global restrictions).
- Fifth column `operation` is a combination of `c`, `r`, `u`, `d`.
- Sixth column `domain` is the optional domain restriction.

---

## Evaluating Expressions with `eval`

Use `eval` for Python expressions, dates, references, and Command operations:

```xml
<record id="action_server_notify" model="ir.actions.server">
    <field name="name">Notify Team</field>
    <field name="model_id" ref="model_project_task"/>
    <field name="state">code</field>
    <!-- Boolean and integer evaluations -->
    <field name="sequence" eval="20"/>
    <!-- Relational link using ref -->
    <field name="binding_model_id" ref="model_project_task"/>
</record>
```

### Relational Commands in `eval`

| Tuple Format | ORM Equivalent | Action |
|--------------|----------------|--------|
| `(4, ref('xml_id'))` | `Command.link(id)` | Add relationship to existing record |
| `(6, 0, [ref('id1'), ref('id2')])` | `Command.set([ids])` | Replace all relationships |
| `(5, 0, 0)` | `Command.clear()` | Remove all relationships |

---

## Noupdate & Data Re-loading

Use `noupdate="1"` on `<odoo>` or `<data>` to create records only once upon module installation without overwriting them on upgrade:

```xml
<odoo noupdate="1">
    <!-- Sequences should not be reset on upgrade -->
    <record id="seq_project_task" model="ir.sequence">
        <field name="name">Task Sequence</field>
        <field name="code">project.task</field>
        <field name="prefix">TSK-</field>
        <field name="padding">5</field>
    </record>
</odoo>
```

