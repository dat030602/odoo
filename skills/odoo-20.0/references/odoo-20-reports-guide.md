# Odoo 20 Reports Guide

## Coding Conventions

- Use parametric `t-call` syntax: `<t t-call="web.external_layout" o="doc"/>`.
- Always use `<t t-out="..."/>` for output (never `t-esc`).
- Declare report action using `<record model="ir.actions.report">`.
- Use standard paper formats from `base.paperformat_euro` or `base.paperformat_us`.

---

## Table of Contents

- [Report Overview](#report-overview)
- [Declaring Report Actions](#declaring-report-actions)
- [QWeb Report Templates](#qweb-report-templates)
- [Parametric `t-call` in Reports](#parametric-t-call-in-reports)
- [Paper Formats & Barcodes](#paper-formats--barcodes)

---

## Report Overview

Odoo generates PDF and HTML documents by rendering QWeb templates and converting HTML to PDF.

### PDF Engines in Odoo 20: Paper Muncher & Wkhtmltopdf
Odoo 20 introduces an in-house rendering engine named **Paper Muncher** (`base_report_paper_muncher`), running in parallel with `base_report_wkhtmltox` (wkhtmltopdf).
- The default engine is configured via system parameter `report.pdf_engine_default` or report attribute `report_type="qweb-pdf-<engine>"`.
- Paper Muncher documentation: [https://odoo.github.io/paper-muncher/](https://odoo.github.io/paper-muncher/)

### Deprecation: Watermark & Background Image Removed
- `res.company` background image and watermark fields have been removed in Odoo 20 without replacement.
- Custom report branding should be implemented via CSS in report templates or custom paper layouts.

---

## Declaring Report Actions

```xml
<record id="action_report_task_summary" model="ir.actions.report">
    <field name="name">Task Summary</field>
    <field name="model">project.task</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">my_module.report_task_summary_template</field>
    <field name="report_file">my_module.report_task_summary_template</field>
    <field name="print_report_name">'Task - %s' % (object.name)</field>
    <field name="binding_model_id" ref="model_project_task"/>
    <field name="binding_type">report</field>
</record>
```

---

## QWeb Report Templates

```xml
<template id="report_task_summary_template">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="doc">
            <!-- Parametric t-call: pass variables directly as attributes -->
            <t t-call="web.external_layout" o="doc">
                <div class="page">
                    <h2 class="mt-4" t-out="doc.name"/>
                    <div class="row mt-3 mb-4">
                        <div class="col-6">
                            <strong>Assignee:</strong>
                            <span t-out="doc.user_id.name or 'Unassigned'"/>
                        </div>
                        <div class="col-6">
                            <strong>Deadline:</strong>
                            <span t-out="doc.date_deadline"/>
                        </div>
                    </div>

                    <table class="table table-sm table-striped">
                        <thead>
                            <tr>
                                <th>Subtask</th>
                                <th class="text-end">Planned Hours</th>
                            </tr>
                        </thead>
                        <tbody>
                            <t t-foreach="doc.child_ids" t-as="subtask">
                                <tr>
                                    <td t-out="subtask.name"/>
                                    <td class="text-end" t-out="subtask.allocated_hours"/>
                                </tr>
                            </t>
                        </tbody>
                    </table>
                </div>
            </t>
        </t>
    </t>
</template>
```

---

## Parametric `t-call` in Reports

In Odoo 20, QWeb supports passing arguments directly as XML attributes on `t-call`:

```xml
<!-- Modern Odoo 20 parametric call -->
<t t-call="my_module.custom_header" title="doc.name" company="doc.company_id"/>

<!-- Literal string argument using .f suffix -->
<t t-call="my_module.custom_footer" message.f="Confidential Document"/>
```

---

## Paper Formats & Barcodes

### Barcodes
Render barcodes dynamically in QWeb using the `/report/barcode` controller endpoint:

```xml
<img t-att-src="'/report/barcode/?barcode_type=%s&amp;value=%s&amp;width=%s&amp;height=%s' %
    ('Code128', doc.code, 600, 100)" style="width:300px;height:50px;"/>
```

