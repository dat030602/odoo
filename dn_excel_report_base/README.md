# Base Excel Report V2

A modern, template-driven Excel report engine for Odoo that eliminates the need for hand-written row insertion and cell mapping code in child modules.

## Overview

`base_excel_report_v2` replaces the old marker-based (`<TABLE_START>`) framework with a Jinja-like template engine that runs natively on `openpyxl` — no LibreOffice dependency required. Child modules only need to implement a single hook method, `_get_report_context()`, which returns a dict. The engine handles all row insertion, style copying, placeholder resolution, and `SUBTOTAL` formula generation automatically.

## Features

- **Template-based**: Design reports visually in Excel using Jinja-like syntax
- **Single hook**: Child modules only implement `_get_report_context()` returning a dict
- **No LibreOffice dependency**: Pure `openpyxl` + `simpleeval`
- **Aggregate filters**: `{{ lines | sum:'amount' }}` generates live `SUBTOTAL` formulas
- **Style preservation**: Row styles are copied automatically during expansion
- **Fast Mode**: Skips heavy per-cell operations for large datasets
- **Framework-agnostic engine**: `TemplateEngine` has zero Odoo imports — fully unit-testable
- **Image support**: `{{ value | image }}` filter embeds base64 or URL images

## Requirements

```bash
pip install openpyxl simpleeval Pillow requests
```

## Module Structure

```
base_excel_report_v2/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── base_excel_report.py       ← TransientModel, hook contract, pipeline
│   └── template_engine.py         ← TemplateEngine (pure Python, no Odoo ORM deps)
├── tests/
│   ├── __init__.py
│   ├── test_template_engine.py    ← unit tests, no Odoo DB required
│   └── test_base_excel_report.py  ← integration tests (TransactionCase)
├── views/
│   └── base_excel_report_views.xml
└── security/
    └── ir.model.access.csv
```

## Template Syntax

### Value Placeholders — `{{ path }}`

```
{{ company.name }}
{{ line.date }}
{{ line.partner.city }}
```

- Dot-path resolution tries `dict.get` first, then `getattr` — works with plain dicts, Odoo recordsets, or nested objects.
- Filter with `|`: `{{ line.amount | fmt:'#,##0.00' }}`, `{{ line.date | fmt:'DD/MM/YYYY' }}`
- Values starting with `=` are written as live Excel formulas.

### Loop Blocks — `{% for x in path %}` ... `{% endfor %}`

```
Row 4:  {% for line in lines %}
Row 5:  {{ line.name }}   B5: {{ line.date }}   C5: {{ line.amount }}
Row 6:  {% endfor %}
```

- Markers must be in the leftmost cell of their row.
- The loop body is all rows between the opening and closing markers.
- Supports multi-row bodies (e.g., a 2-row card layout per record).
- **Nested loops are not yet supported** (planned for Giai đoạn 2).

### Conditional Blocks — `{% if expr %}` ... `{% endif %}`

```
A9:  {% if line.amount > 1000000 %}
B9:  {{ line.name }}  (VIP)
A10: {% endif %}
```

- Conditions are evaluated with `simpleeval` (safe — no arbitrary Python execution).

### Aggregate Filters — `sum`, `count`, `avg`, `max`, `min`

```
{{ lines | sum:'amount' }}
```

- Must appear **outside** the `for` block it aggregates.
- Generates `=SUBTOTAL(code, col_start:col_end)` referencing the actual expanded row range.

| Filter | `SUBTOTAL` code |
|--------|-----------------|
| `sum`  | 9               |
| `avg`  | 1               |
| `count`| 2               |
| `max`  | 4               |
| `min`  | 5               |

### Image Filter — `image`

```
{{ line.photo_base64 | image }}
{{ company.logo_url | image:width=120,height=60 }}
```

- Supports base64-encoded image data or URLs (http/https)
- Optional `width` and `height` parameters for resizing (in pixels)
- Images are embedded using `openpyxl.drawing.image.Image`
- In loop blocks, each item gets its own image at the correct position

## Creating a Child Module

### 1. Template File (`template_sale_report.xlsx`)

```
Row 1:  {{ company.name }}
Row 2:  Report printed on {{ print_date }}
Row 3:  Order            Date              Amount
Row 4:  {% for line in lines %}
Row 5:  {{ line.name }}  {{ line.date | fmt:'DD/MM/YYYY' }}  {{ line.amount | fmt:'#,##0.00' }}
Row 6:  {% endfor %}
Row 7:  Grand Total                        {{ lines | sum:'amount' }}
```

### 2. Python Model

```python
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

### 3. Manifest

```python
{
    'name': 'Sale Excel Report',
    'version': '19.0.1.0.0',
    'depends': ['base_excel_report_v2', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_sale_excel_report_views.xml',
    ],
}
```

## Hook Method Reference

| Method | Required | Returns |
|--------|----------|---------|
| `_get_template_name()` | ✅ | `str` — attachment name |
| `_get_report_context()` | ✅ | `dict` — arbitrarily nested data |
| `_get_output_filename()` | ⬜ | `str` — defaults to `{template_base}_output.xlsx` |

## Testing

### Unit Tests (no Odoo DB required)

```bash
cd /opt/odoo19/dev/dn_excel_report_base
pip install openpyxl simpleeval pytest
pytest tests/test_template_engine.py -v --import-mode=importlib --rootdir=tests --confcutdir=tests
```

### Integration Tests (requires Odoo)

```bash
odoo-bin test -i base_excel_report_v2 --test-enable -d <database>
```

## Migration from `base_excel_report` (V1)

| V1 Concept | V2 Equivalent |
|------------|---------------|
| `<TABLE_START>` marker | `{% for x in path %}` / `{% endfor %}` pair |
| `_get_report_data()` returning Recordset/list | Build the equivalent list inside `_get_report_context()['lines']` |
| `_write_table_data(sheet, data, start_row, start_col)` | Delete — replaced by `{{ line.field }}` in the template |
| `_get_header_footer_data()` returning `{'{{KEY}}': value}` | Delete — put values straight into the context dict, reference as `{{ key }}` in the template |
| Grand Total placeholder + manual `SUBTOTAL` formula string | `{{ lines \| sum:'field' }}` |
| Fast Mode (`FAST_MODE_THRESHOLD`) | Not yet ported — see Known Limitations |

**Migration is not automatic.** Existing `.xlsx` templates using `<TABLE_START>` will not work with `base_excel_report_v2` — templates must be rewritten with `{% for %}` markers.

## Server Action Integration (Odoo 19)

For reports that don't need a custom filter UI, you can configure Excel report generation through the Odoo UI using Server Actions — no new Python files required.

### How It Works

1. Upload a `.xlsx` template to **Attachments** and check **Is Excel Template**
2. Create a **Server Action** with:
   - **Action To Do:** Generate Excel From Template
   - **Excel Template:** Select your uploaded template
   - **Python Code:** Build the `excel_context` dict
3. Click **Create Contextual Action** to add it to the model's Action menu
4. From the list view: select records → Action → *(your action)* → Run

### Python Code Example

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

### Available Variables

| Variable | Description |
|----------|-------------|
| `env` | Odoo environment |
| `model` | Model name of the action's target model |
| `record` | First selected record (if any) |
| `records` | All selected records (Recordset) |
| `user` | Current user |
| `fields` | Odoo fields module |

### Key Points

- The `_multi` suffix on `_run_action_excel_template_multi` ensures all selected records are processed in a single call, producing one Excel file
- The `code` field is restricted to `base.group_system` (technical users only)
- Odoo 19 automatically tracks version history of the Python code via `ir.actions.server.history`
- Use the child-module pattern (Section "Creating a Child Module") when a report needs its own filter form or per-report ACLs

## Known Limitations

1. **Merged cells inside a loop body are not handled.** `insert_rows()` / `_copy_row()` do not detect or re-create `MergedCellRange`s.
2. **Static images do not shift.** A logo placed below a `for` block will not move down when the block expands.
3. **Nested `for` is parsed but not expanded** — raises `TemplateError` with a clear message.
5. **Fast Mode is not ported.** Every render does full per-cell style copying.
6. **Cross-sheet and 3D formula references** are not verified safe across `insert_rows()`/`delete_rows()`.

## License

LGPL-3
