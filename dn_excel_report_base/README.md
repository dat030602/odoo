# Base Excel Report

**Template-based Excel report engine with Jinja-like syntax for Odoo.**

A modern, template-driven Excel report engine for Odoo that eliminates the need for hand-written row insertion and cell mapping code in child modules. Design your reports visually in Excel using Jinja-like syntax — no LibreOffice dependency, pure `openpyxl` + `simpleeval`.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Module Structure](#2-module-structure)
3. [Installation & Dependencies](#3-installation--dependencies)
4. [Manifest Attributes Reference](#4-manifest-attributes-reference)
5. [Template Syntax Reference](#5-template-syntax-reference)
6. [Core Implementation](#6-core-implementation)
7. [Base Model — `base.excel.report`](#7-base-model--baseexcelreport)
8. [Hook Method Reference](#8-hook-method-reference)
9. [Creating a Child Module — Step by Step](#9-creating-a-child-module--step-by-step)
10. [Server Action Integration (Odoo 19)](#10-server-action-integration-odoo-19)
11. [Performance Modes](#11-performance-modes)
12. [Error Reference](#12-error-reference)
13. [Known Limitations](#13-known-limitations)
14. [Quick Reference Card](#14-quick-reference-card)

---

## 1. Overview

`dn_excel_report_base` replaces hand-written `_write_table_data()` / `_get_header_footer_data()` hooks with a **single JSON context** produced by the child module, matched against a `.xlsx` template that declares its own loops and placeholders inline — similar in spirit to `report_py3o` (Genshi on ODF) but running natively on `openpyxl`, with no LibreOffice dependency.

**Child module responsibility shrinks to one hook:**

```python
def _get_report_context(self):
    return {"company": {...}, "lines": [...]}
```

Everything else — inserting rows, copying styles, replacing placeholders, computing `SUBTOTAL` formulas — is handled by `TemplateEngine`.

### Key Features

- **Template-based**: Design reports visually in Excel using Jinja-like syntax.
- **Jinja-like syntax**: `{% for %}`, `{% if %}`, `{{ placeholder }}`, and filters.
- **Single hook**: Child modules only implement `_get_report_context()` returning a dict.
- **No LibreOffice dependency**: Pure `openpyxl` + `simpleeval`.
- **Aggregate filters**: `{{ lines | sum:'amount' }}` generates live `SUBTOTAL` formulas.
- **Style preservation**: Row styles are copied automatically during expansion.
- **Fast Mode**: Skips heavy per-cell operations for large datasets.

---

## 2. Module Structure

```
dn_excel_report_base/
├── __manifest__.py          ← Module metadata (name, version, depends, data, etc.)
├── __init__.py              ← Python package init, imports subpackages
├── change.md                ← Technical developer guide (design rationale, migration)
├── pytest.ini               ← pytest configuration for standalone unit tests
├── requirement.txt          ← Python dependencies (openpyxl, simpleeval, Pillow, requests)
├── README.md                ← This file
├── models/
│   ├── __init__.py          ← Imports all model files
│   ├── base_excel_report.py ← TransientModel, hook contract, processing pipeline
│   ├── template_engine.py   ← TemplateEngine (pure Python, no Odoo ORM deps)
│   ├── ir_actions_server.py ← Server Action integration (Odoo 19)
│   └── ir_attachment.py     ← ir.attachment extension (is_excel_template flag)
├── security/
│   └── ir.model.access.csv  ← Access control rules for model permissions
├── tests/
│   ├── test_base_excel_report.py  ← Integration tests (TransactionCase)
│   └── test_template_engine.py    ← Unit tests, no Odoo DB required
└── views/
    ├── base_excel_report_views.xml     ← Wizard form view (choose/download states)
    └── ir_actions_server_views.xml     ← Server Action form view extension
```

`template_engine.py` is deliberately **framework-agnostic** — it operates on an `openpyxl.Worksheet` and a plain `dict`/`list` context, with zero Odoo imports. This lets you unit-test it outside Odoo entirely.

---

## 3. Installation & Dependencies

### Python Dependencies

```bash
pip install openpyxl simpleeval Pillow requests
```

| Package | Purpose |
|---|---|
| `openpyxl` | Read/write `.xlsx` files |
| `simpleeval` | Safe expression evaluation for `{% if %}` conditions — **do not use bare `eval()`** on user-uploaded template strings |
| `Pillow` | Image resizing for the `image` filter (optional, Giai đoạn 3) |
| `requests` | Fetching images from URLs for the `image` filter (optional, Giai đoạn 3) |

### Odoo Dependencies

```python
'depends': ['base', 'web'],
```

### Odoo Shell Sanity Check

```python
import openpyxl, simpleeval
print(openpyxl.__version__, simpleeval.__version__)
```

### Installation Steps

1. Copy the module folder to your Odoo `addons` path.
2. Update the apps list: **Apps → Update Apps List**.
3. Search for "Base Excel Report" and click **Install**.
4. Upload your `.xlsx` template to **Settings → Technical → Database Structure → Attachments**.

---

## 4. Manifest Attributes Reference

The `__manifest__.py` file defines all module metadata. Below is a complete reference of every attribute used in this module, with descriptions of what each controls.

### Core Metadata

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable module name displayed in the Apps list. |
| `version` | `str` | Module version string. Follows Odoo's `odoo.series.x.y.z` convention (e.g., `19.0.2.0.0`). |
| `category` | `str` | Module category for filtering in Apps view (e.g., `Technical`, `Sales`, `Accounting`). |
| `summary` | `str` | One-line summary shown in the Apps grid. |
| `description` | `str` | Full module description (can be multi-line). Shown on the module's detail page. |
| `author` | `str` | Author name or company. |
| `license` | `str` | SPDX license identifier (e.g., `LGPL-3`, `OPL-1`, `GPL-2`). |
| `website` | `str` | Module website URL (not used in this module but commonly included). |
| `maintainer` | `str` | Maintainer contact (not used in this module but commonly included). |

### Dependencies

| Attribute | Type | Description |
|---|---|---|
| `depends` | `list[str]` | List of Odoo module names this module depends on. Odoo ensures these are installed first. |
| `external_dependencies` | `dict` | External (non-Odoo) dependencies. Sub-keys: `python` (pip packages), `deb` (system packages). |

### Data Files

| Attribute | Type | Description |
|---|---|---|
| `data` | `list[str]` | List of XML/CSV data files loaded at install and upgrade. Loaded in order. |
| `demo` | `list[str]` | Demo data files loaded only when demo mode is enabled. |
| `qweb` | `list[str]` | QWeb template files (`.xml` with `<template>` definitions). |
| `init_xml` | `list[str]` | Deprecated; use `data` instead. |
| `update_xml` | `list[str]` | Deprecated; use `data` instead. |
| `installable` | `bool` | Whether the module can be installed from the Apps view. Set to `True` to make it visible. |
| `application` | `bool` | Whether this module is an "application" (appears in the main dashboard with an icon). |
| `auto_install` | `bool` | Whether the module auto-installs when all its dependencies are installed. |
| `assets` | `dict` | Asset bundles for CSS/JS (e.g., `{'web.assets_backend': ['my_module/static/src/js/file.js']}`). |

### Security & Access

| Attribute | Type | Description |
|---|---|---|
| `installable` | `bool` | Must be `True` for the module to appear in the Apps list. |
| `application` | `bool` | If `True`, the module appears as an application icon on the dashboard. |

### Manifest Example (This Module)

```python
{
    'name': 'Base Excel Report',
    'version': '19.0.2.0.0',
    'category': 'Technical',
    'summary': 'Template-based Excel report engine with Jinja-like syntax for Odoo.',
    'description': """
Base Excel Report
====================

A modern, template-driven Excel report engine for Odoo...
""",
    'author': 'Dat Nguyen',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/base_excel_report_views.xml',
        'views/ir_actions_server_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl', 'simpleeval', 'Pillow', 'requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

---

## 5. Template Syntax Reference

### 5.1 Placeholders — `{{ path }}`

```
{{ company.name }}
{{ line.date }}
{{ line.partner.city }}
{{ line.amount | fmt:'#,##0.00' }}
```

- Path resolution tries `dict.get` first, then `getattr` — works transparently with plain dicts, Odoo recordsets, or nested objects.
- `| fmt:'...'` sets `cell.number_format` instead of embedding the format in the string.
- A resolved value starting with `=` is written as a live Excel formula.

### 5.2 Loop Blocks — `{% for x in path %}` … `{% endfor %}`

```
A4:  {% for line in lines %}
A5:  {{ line.name }}   B5: {{ line.date }}   C5: {{ line.amount }}
A6:  {% endfor %}
```

- Marker must be the **only content** of the leftmost non-empty cell in its row.
- The loop body is every row strictly between the two marker rows (1 or more rows per item is supported — e.g., a 2-row card layout per record).
- Supports **flat** `for` only in Giai đoạn 1. Nesting is planned for Giai đoạn 2.

### 5.3 Conditionals — `{% if expr %}` … `{% endif %}`

```
A9:  {% if line.amount > 1000000 %}
B9:  {{ line.name }} (VIP)
A10: {% endif %}
```

- `expr` is evaluated with `simpleeval.EvalWithCompoundTypes`, context = current loop variables only (no arbitrary Python).

### 5.4 Aggregate Filters — `sum`, `count`, `avg`, `max`, `min`

```
{{ lines | sum:'amount' }}
```

Must appear **outside** the `for` block it aggregates. Compiled to:

```
=SUBTOTAL(9, C10:C14)
```

| Filter | `SUBTOTAL` code |
|---|---|
| `sum` | 9 |
| `avg` | 1 |
| `count` | 2 |
| `max` | 4 |
| `min` | 5 |

### 5.5 Image Filter — `image`

```
{{ line.photo_base64 | image }}
{{ company.logo_url | image:width=120,height=60 }}
```

Not implemented in Giai đoạn 1 — stubbed with a clear `TemplateError` pointing to Section 13.

### 5.6 Format Filter — `fmt`

```
{{ line.amount | fmt:'#,##0.00' }}
{{ line.date | fmt:'DD/MM/YYYY' }}
```

Sets the cell's `number_format` attribute rather than converting the value to a formatted string. This preserves the underlying numeric/date value for Excel calculations.

### 5.7 Loop Variables

Inside a `{% for %}` block, the following special variables are available:

| Variable | Description |
|---|---|
| `loop.index` | 1-based iteration index |
| `loop.index0` | 0-based iteration index |
| `loop.first` | `True` on the first iteration |
| `loop.last` | `True` on the last iteration |
| `loop.length` | Total number of items |

---

## 6. Core Implementation

### 6.1 `TemplateEngine` Class

```python
# models/template_engine.py
class TemplateEngine:
    def __init__(self, sheet: Worksheet, marker_column: int = 1):
        self.sheet = sheet
        self.marker_column = marker_column
        self.expanded_ranges: dict[str, tuple[int, int]] = {}
```

The engine processes the worksheet through the following pipeline:

1. `parse_blocks()` — Find all `{% for %}` / `{% if %}` blocks using a stack
2. `expand()` — Expand blocks recursively (deepest first)
3. `resolve_placeholders()` — Replace remaining `{{ }}` placeholders
4. `resolve_sum_filters()` — Convert aggregate filters to `SUBTOTAL` formulas
5. `embed_images()` — Handle `{{ x | image }}` filters (Giai đoạn 3)

### 6.2 Block Parsing (`parse_blocks`)

Scans the marker column top-to-bottom, matching `{% %}` pairs with a stack so nested blocks parse correctly.

### 6.3 Block Expansion (`expand_for_block`)

Expands a `{% for %}` block by duplicating its body for each item. Handles child `{% if %}` blocks within the loop body by evaluating them for each iteration.

### 6.4 Placeholder Resolution (`resolve_placeholders`)

Resolves all `{{ }}` placeholders in the worksheet or a specific row range. Skips aggregate filter expressions (handled separately by `resolve_sum_filters`).

### 6.5 Aggregate Filters (`resolve_sum_filters`)

Converts `{{ list_name | filter:'field' }}` expressions into `=SUBTOTAL(code, col_start:col_end)` formulas referencing the actual expanded row range of the corresponding loop.

### 6.6 Path Resolution (`resolve_path`)

```python
@staticmethod
def resolve_path(path: str, context: dict) -> Any:
    parts = path.split('.')
    current: Any = context
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current
```

Tries `dict.get` first, then `getattr` — works transparently with plain dicts, Odoo recordsets, or nested objects.

### 6.7 Image Embedding (`embed_images`)

Processes all `__IMAGE__` markers and embeds actual images. Supports base64-encoded image data, URLs (http/https), and optional width/height resizing via PIL.

---

## 7. Base Model — `base.excel.report`

```python
class BaseExcelReport(models.TransientModel):
    _name = 'base.excel.report'
    _description = 'Base Excel Template Report (V2 Engine)'
```

### Fields

| Field | Type | Description |
|---|---|---|
| `excel_file` | `Binary` | Generated Excel file. Available after clicking "Generate Report". |
| `file_name` | `Char` | Name of the generated Excel file presented for download. |
| `state` | `Selection` | Wizard state: `choose` (configure) or `download` (file ready). |

### Processing Pipeline (`action_generate_excel`)

1. **Step 1** → `_load_template()`: Fetch attachment, decode base64, load into `BytesIO` RAM buffer.
2. **Step 2** → `_get_report_context()` [HOOK]: Child returns a dict with all data needed for rendering.
3. **Step 3** → `TemplateEngine.render()`: Parse blocks, expand loops, resolve placeholders, generate `SUBTOTAL` formulas.
4. **Step 4** → `_autofit_columns()`: Widen columns to fit data (Normal Mode only).
5. **Step 5** → `_export_file()`: Save workbook → `BytesIO` → base64 → wizard download state.

### Private Pipeline Methods (Do NOT Override)

| Method | Description |
|---|---|
| `_load_template()` | Fetches the Excel template attachment and loads it non-destructively into RAM. |
| `_autofit_columns(sheet, start_row, end_row)` | Widens each column to accommodate the longest content within the data rows. |
| `_export_file(wb, file_name=None)` | Serializes the populated workbook to base64 and exposes it for download. |
| `_generate_from_attachment(name, attachment, context)` | Shared entry point for both the hook-based wizard flow and the Server Action flow. |

---

## 8. Hook Method Reference

| Method | Required | Signature | Returns |
|---|---|---|---|
| `_get_template_name` | ✅ | `(self)` | `str` — attachment name (e.g., `'template_sale_report.xlsx'`) |
| `_get_report_context` | ✅ | `(self)` | `dict` — arbitrarily nested dicts/lists/recordsets |
| `_get_output_filename` | ⬜ | `(self)` | `str`, defaults to `{template_base}_output.xlsx` |

### `_get_template_name()`

```python
def _get_template_name(self):
    """Return the exact filename of the Excel template in ir.attachment.

    The framework searches ir.attachment with domain
    [('name', '=', <returned_value>)]

    Returns:
        str: Filename including extension (e.g. 'template_sale_report.xlsx').

    Raises:
        NotImplementedError: Always — must be overridden by child module.
    """
    raise NotImplementedError(
        f'[{self._name}] _get_template_name() must be implemented in the child module.'
    )
```

### `_get_report_context()`

```python
def _get_report_context(self):
    """Return the report context as a dict.

    This is the single required hook for child modules. The returned dict
    is passed directly to TemplateEngine.render() and used to resolve
    all {{ }} placeholders and {% for %} / {% if %} blocks in the template.

    Returns:
        dict: Arbitrarily nested dict containing all data needed for
              template rendering.

    Raises:
        NotImplementedError: Always — must be overridden by child module.
    """
    raise NotImplementedError(
        f'[{self._name}] _get_report_context() must be implemented in the child module.'
    )
```

### `_get_output_filename()`

```python
def _get_output_filename(self, file_name=None):
    """Return the filename for the generated (output) Excel file.

    Override this in child modules to provide a more descriptive or
    date-stamped filename.

    Returns:
        str: Output filename including .xlsx extension.
    """
    if file_name:
        template_name = file_name
    else:
        template_name = self._get_template_name()
    return (
        template_name
        .replace('template_', '', 1)
        .replace('.xlsx', '_output.xlsx')
    )
```

---

## 9. Creating a Child Module — Step by Step

### 9.1 Template File (`template_sale_report.xlsx`)

```
Row 1:  {{ company.name }}
Row 2:  Report printed on {{ print_date }}
Row 3:  (blank — column headers, styled manually in Excel)
Row 4:  Order            Date              Amount
Row 5:  {% for line in lines %}
Row 6:  {{ line.name }}  {{ line.date | fmt:'DD/MM/YYYY' }}  {{ line.amount | fmt:'#,##0.00' }}
Row 7:  {% endfor %}
Row 8:  Grand Total                        {{ lines | sum:'amount' }}
```

### 9.2 Python Model

```python
# wizard/wizard_sale_excel_report.py
from odoo import models, fields


class SaleExcelReport(models.TransientModel):
    _name = 'sale.excel.report'
    _inherit = 'base.excel.report'
    _description = 'Sale Excel Report'

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')

    def _get_template_name(self):
        return 'template_sale_report.xlsx'

    def _get_report_context(self):
        domain = [('state', 'in', ['sale', 'done'])]
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        orders = self.env['sale.order'].search(domain, order='date_order asc')

        return {
            'company': {'name': self.env.company.name},
            'print_date': fields.Date.today().strftime('%d/%m/%Y'),
            'lines': [
                {
                    'name': o.name,
                    'date': o.date_order.date(),
                    'amount': o.amount_total,
                }
                for o in orders
            ],
        }

    def _get_output_filename(self):
        date_str = fields.Date.today().strftime('%Y%m%d')
        return f'Sale_Report_{date_str}.xlsx'
```

### 9.3 Manifest

```python
{
    'name': 'Sale Excel Report',
    'version': '16.0.1.0.0',
    'depends': ['dn_excel_report_base', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_sale_excel_report_views.xml',
    ],
}
```

### 9.4 View XML (Inherit Base Wizard)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_sale_excel_report_form" model="ir.ui.view">
        <field name="name">sale.excel.report.form</field>
        <field name="model">sale.excel.report</field>
        <field name="inherit_id" ref="dn_excel_report_base.view_base_excel_report_form"/>
        <field name="arch" type="xml">
            <xpath expr="//group[@name='filter_area']" position="inside">
                <group>
                    <field name="date_from"/>
                    <field name="date_to"/>
                </group>
            </xpath>
        </field>
    </record>

    <record id="action_sale_excel_report" model="ir.actions.act_window">
        <field name="name">Sale Excel Report</field>
        <field name="res_model">sale.excel.report</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>

    <menuitem id="menu_sale_excel_report"
              name="Sale Excel Report"
              parent="base.menu_reports"
              action="action_sale_excel_report"/>
</odoo>
```

### 9.5 Access Control

```csv
# security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sale_excel_report_user,access.sale.excel.report.user,model_sale_excel_report,base.group_user,1,1,1,1
```

---

## 10. Server Action Integration (Odoo 19)

### 10.1 Why Server Action Instead of a Child Module

For reports that don't need a custom filter UI beyond a domain/selection already available on the source model's list view, the child-module scaffolding is unnecessary. `ir.actions.server` already provides the entry point: a record users configure through the UI, bound to a model, with a `code` field for short Python snippets and a **Run** button.

**What stays exactly as-is:** `template_engine.py` and the core of `base_excel_report.py` — this integration only adds a dispatch branch.

**What this trades away:** per-report `ir.model.access.csv` entries, a dedicated wizard form for custom filters, and compile-time type safety on the context-building code.

### 10.2 `ir.attachment` Extension

```python
# models/ir_attachment.py
from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_excel_template = fields.Boolean(
        string='Is Excel Template',
        help="Marks this attachment as selectable in the "
             "'Generate Excel From Template' server action.",
    )
```

### 10.3 `ir.actions.server` Extension

```python
# models/ir_actions_server.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    state = fields.Selection(
        selection_add=[('excel_template', 'Generate Excel From Template')],
        ondelete={'excel_template': 'cascade'},
    )
    excel_template_name = fields.Char(
        string='Excel Template Name',
        help="Name of the Excel template file in Attachments "
             "with 'Is Excel Template' checked.",
    )
    excel_template_attachment = fields.Binary(
        string='Excel Template',
        help="Template file uploaded to Attachments with "
             "'Is Excel Template' checked.",
    )

    def _warning_depends(self):
        return super()._warning_depends() + ['excel_template_attachment']

    def _get_warning_messages(self):
        warnings = super()._get_warning_messages()
        if self.state == 'excel_template' and not self.excel_template_attachment:
            warnings.append(_(
                "Select an Excel template when using "
                "'Generate Excel From Template'."
            ))
        return warnings

    def _run_action_excel_template_multi(self, eval_context=None):
        self.ensure_one()
        if not self.excel_template_attachment:
            raise UserError(_(
                "No Excel template selected for this server action."
            ))

        safe_eval(
            self.sudo().code.strip(), eval_context,
            mode='exec', filename=str(self),
        )
        report_context = eval_context.get('excel_context')
        if not isinstance(report_context, dict):
            raise UserError(_(
                "The Python code must set a variable named "
                "'excel_context' to a dict. Available variables: env, "
                "model, record, records (see the code editor's help tab)."
            ))

        wizard = self.env['base.excel.report'].create({})
        return wizard._generate_from_attachment(
            self.excel_template_name, self.excel_template_attachment, report_context
        )
```

### 10.4 End-to-End Usage Example

1. Upload `template_sale_report.xlsx` to **Attachments**, check **Is Excel Template**.
2. **Settings → Technical → Actions → Server Actions → New**.
   - **Model:** `sale.order`
   - **Action To Do:** Generate Excel From Template
   - **Excel Template:** `template_sale_report.xlsx`
   - **Python Code:**
     ```python
     excel_context = {
         "company": {"name": env.company.name},
         "print_date": fields.Date.today().strftime('%d/%m/%Y'),
         "lines": [
             {"name": o.name, "date": o.date_order.date(), "amount": o.amount_total}
             for o in records
         ],
     }
     ```
3. Click **Create Contextual Action** so the action appears in the Action menu on `sale.order`'s list view.
4. From the list view: select rows → **Action → *(action name)* → Run**.

### 10.5 Odoo 16 → 19 Differences

| | 16.0 | 19.0 | Effect |
|---|---|---|---|
| Groups field name | `groups_id` | `group_ids` | Not touched by our code |
| `_get_runner()` fallback | Falls back to deprecated public names | Fallback removed | We always use the private-prefixed name |
| `code` field default | Pre-filled sample | Empty | Cosmetic only |
| Config-error UX | Hard `@api.constrains` | `_get_warning_messages()` banner | We used the 19-native warning pattern |
| Code change tracking | None | `ir.actions.server.history` auto-records | Free bonus: built-in version history |
| `ir.actions.act_url` target | `new`, `self` | Adds `download` | Not adopted — more moving parts for no gain |

### 10.6 Caveats

1. **`code` is still `safe_eval`, not a real sandbox.** Restricted to `base.group_system`.
2. **`_multi` is mandatory.** Without the suffix, Odoo calls it once per `active_id`, generating N separate files.
3. **No per-report ACLs.** Every `base.group_system` user can configure any template.
4. **`records` is only populated when the action is bound correctly.** Must be triggered from the model it's bound to.

---

## 11. Performance Modes

### Normal Mode (records < `FAST_MODE_THRESHOLD`)

- Full per-cell style copy from template row to inserted rows.
- Column auto-fit after data write.

### Fast Mode (records >= `FAST_MODE_THRESHOLD`)

- Skips `_copy_row_styles()` → relies on column-level template formatting.
- Skips `_autofit_columns()`.

### Constants

| Constant | Default | Description |
|---|---|---|
| `FAST_MODE_THRESHOLD` | `1000` | Record count at which the framework switches to Fast Mode. Typical safe range: 500–2000. |
| `MAX_COLUMN_WIDTH` | `50` | Upper bound for auto-fit column width (in Excel character units). |
| `COLUMN_WIDTH_FONT_FACTOR` | `1.2` | Multiplier applied to character count when calculating column width. |
| `COLUMN_WIDTH_PADDING` | `2` | Extra character units added to the calculated width for visual breathing room. |

---

## 12. Error Reference

| Error | Root Cause | Resolution |
|---|---|---|
| `Unclosed '{% for %}' opened at row N` | Missing `{% endfor %}` | Add the closing marker |
| `Unmatched '{% endfor %}' at row N: no open block.` | Extra/orphaned closing marker | Remove it or add the matching opener |
| `Mismatched block at row N` | `{% endif %}` closing a `for`, or vice versa | Fix marker pairing |
| `Empty loop body for '{% for ... %}'` | Opening and closing marker on adjacent rows with nothing between | Add at least one body row |
| `Aggregate filter 'sum' at row N references 'X', which is not a known expanded loop variable name` | `{{ X \| sum:'field' }}` doesn't match any `{% for x in X %}` name | Match the iterable name used in the loop, not the item name |
| `Image filter used outside a supported context` | `\| image` used — Giai đoạn 1 has no image support | See Section 13; defer to Giai đoạn 3 |
| `_get_template_name() must be implemented` | Child forgot the hook | Add override |
| `_get_report_context() must be implemented` | Child forgot the hook | Add override |
| `_get_report_context() must return a dict, got list` | Hook returns wrong top-level type | Wrap in a dict, e.g. `{'lines': [...]}` |
| `Failed to evaluate condition '...'` | Bad `{% if %}` expression or referenced name not in context | Check spelling and available variables at that scope |
| `Template file '...' was not found in Attachments.` | Template not uploaded or name mismatch | Upload to ir.attachment with exact Name match |
| `Failed to read the Excel template '...'` | File is not a valid .xlsx workbook | Ensure the file is a valid .xlsx |

---

## 13. Known Limitations

These are carried over from the design spec's risk analysis and remain **unresolved in the reference code**:

1. **Merged cells inside a loop body are not handled.** `insert_rows()` / `_copy_row()` do not detect or re-create `MergedCellRange`s. A template with a merged cell inside `{% for %}...{% endfor %}` will produce corrupted or duplicated merge ranges.
2. **Static images do not shift.** A logo placed below a `for` block will not move down when the block expands. Keep static images above the first loop.
3. **`image` filter is unimplemented** — raises `TemplateError` if used. Planned for Giai đoạn 3.
4. **Nested `for` is parsed but not expanded** — `parse_blocks()` builds the correct `children` tree, but `expand_for_block()` only processes top-level blocks. Using nested loops will silently leave inner `{% for %}` markers unexpanded as literal text.
5. **Fast Mode is not ported.** Every render does full per-cell style copying regardless of row count.
6. **Cross-sheet and 3D formula references** are not verified safe across `insert_rows()`/`delete_rows()`. Test explicitly if a template's `for` block sits above/beside such formulas.

---

## 14. Quick Reference Card

### Template Syntax

```
{{ path.to.value }}                    value substitution
{{ value | fmt:'#,##0.00' }}           number/date format
{% for x in path %} ... {% endfor %}   loop block (flat only, Giai đoạn 1)
{% if expr %} ... {% endif %}          conditional block
{{ list_name | sum:'field' }}          =SUBTOTAL(9,...) over the expanded range
{{ list_name | count:'field' }}        =SUBTOTAL(2,...)
{{ list_name | avg:'field' }}          =SUBTOTAL(1,...)
{{ list_name | max:'field' }}          =SUBTOTAL(4,...)
{{ list_name | min:'field' }}          =SUBTOTAL(5,...)
```

### Child Module Contract

```python
class MyExcelReport(models.TransientModel):
    _name = 'my.excel.report'
    _inherit = 'base.excel.report'

    def _get_template_name(self):
        return 'template_my_report.xlsx'

    def _get_report_context(self):
        return {'lines': [...], 'company': {...}}
```

### Pre-flight Checklist for a New Template

```
□  Every {% for %} has a matching {% endfor %} (marker cell = leftmost column, exact syntax)
□  No nested {% for %} yet (Giai đoạn 1 limitation — see Section 13)
□  {{ list_name | sum:'field' }} uses the SAME name as the for-loop's iterable path
□  No merged cells inside any loop body
□  No static images below a loop block
□  Saved as .xlsx, uploaded to ir.attachment with Name == _get_template_name()
```

---

## License

LGPL-3