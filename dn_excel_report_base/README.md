# Base Excel Report — Odoo Technical Developer Guide

> **Module:** `dn_excel_report_base`  
> **Odoo Version:** 16.0 (compatible patterns apply to 14.0 / 15.0 / 17.0)  
> **Last Updated:** 2026-07-31  
> **License:** LGPL-3  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture Philosophy](#2-architecture-philosophy)
3. [Module Structure](#3-module-structure)
4. [Installation & Dependencies](#4-installation--dependencies)
5. [Template Design Contract](#5-template-design-contract)
   - 5.1 [TABLE_START Marker](#51-table_start-marker)
   - 5.2 [Placeholder Syntax](#52-placeholder-syntax)
   - 5.3 [Grand Total Row](#53-grand-total-row)
   - 5.4 [Column-Level Formatting (Fast Mode)](#54-column-level-formatting-fast-mode)
   - 5.5 [Header & Grand Total Override](#55-header--grand-total-override)
   - 5.6 [Uploading the Template](#56-uploading-the-template)
6. [Processing Pipeline](#6-processing-pipeline)
7. [Hook Methods Reference](#7-hook-methods-reference)
   - 7.1 [Required Hooks](#71-required-hooks)
   - 7.2 [Optional Hooks](#72-optional-hooks)
8. [Performance Modes](#8-performance-modes)
   - 8.1 [Normal Mode](#81-normal-mode)
   - 8.2 [Fast Mode](#82-fast-mode)
   - 8.3 [Tuning the Threshold](#83-tuning-the-threshold)
9. [Group & Subtotal Reports](#9-group--subtotal-reports)
   - 9.1 [Data Flattening Pattern](#91-data-flattening-pattern)
   - 9.2 [SUBTOTAL vs SUM — Avoiding Double Count](#92-subtotal-vs-sum--avoiding-double-count)
10. [Row-Level Formulas](#10-row-level-formulas)
11. [Creating a Child Module — Step-by-Step](#11-creating-a-child-module--step-by-step)
    - 11.1 [Python Model](#111-python-model)
    - 11.2 [View Inheritance](#112-view-inheritance)
    - 11.3 [Manifest](#113-manifest)
12. [Module-Level Constants](#12-module-level-constants)
13. [Error Reference](#13-error-reference)
14. [Choosing the Right Library](#14-choosing-the-right-library)
    - 14.1 [openpyxl (This Framework)](#141-openpyxl-this-framework)
    - 14.2 [xlsxwriter](#142-xlsxwriter)
    - 14.3 [pandas](#143-pandas)
    - 14.4 [Recommended Hybrid Strategy](#144-recommended-hybrid-strategy)
15. [Quick Reference Card](#15-quick-reference-card)

---

## 1. Overview

`base_excel_report` is a reusable Odoo framework for generating formatted
Excel reports from visually pre-designed `.xlsx` template files.

### Core Idea

Instead of writing Python code to draw borders, set colors, merge cells, or
position logos — a **business analyst or template designer** creates the report
layout directly in Microsoft Excel. The Python backend only handles:

- Finding the data insertion point inside the template.
- Inserting the correct number of rows.
- Pushing data values into cells.
- Replacing dynamic placeholder strings.

Every child module (e.g. Sale Report, Inventory Report, HR Payroll Report)
inherits this base and overrides **3–4 short hook methods** totalling roughly
**30–50 lines** of module-specific code, regardless of the report's visual
complexity.

### What This Framework Handles (So Child Modules Don't Have To)

| Concern | Handled By |
|---|---|
| Decoding base64 attachment binary | `_load_template()` |
| Locating the insertion row in the sheet | `_find_table_marker()` |
| Inserting blank rows | `action_generate_excel()` |
| Copying cell styles to inserted rows | `_copy_row_styles()` |
| Scanning and replacing `{{PLACEHOLDER}}` strings | `_replace_placeholders()` |
| Auto-fitting column widths | `_autofit_columns()` |
| Serialising workbook to base64 for download | `_export_file()` |
| Switching between Normal / Fast mode | `action_generate_excel()` |

---

## 2. Architecture Philosophy

This framework follows the **Template Method design pattern**:

```
BaseExcelReport         (defines the algorithm skeleton)
    │
    ├── action_generate_excel()   ← runs the full pipeline (do not override)
    │       │
    │       ├── _load_template()              (private, do not override)
    │       ├── _find_table_marker()          (private, do not override)
    │       ├── _get_report_data()            ← HOOK — child must override
    │       ├── _copy_row_styles()            (private, do not override)
    │       ├── _write_table_data()           ← HOOK — child must override
    │       ├── _get_header_footer_data()     ← HOOK — child may override
    │       ├── _replace_placeholders()       (private, do not override)
    │       ├── _autofit_columns()            (private, do not override)
    │       └── _export_file()                (private, do not override)
    │
    └── _get_template_name()                  ← HOOK — child must override
        _get_output_filename()                ← HOOK — child may override


SaleExcelReport(_inherit = 'base.excel.report')
    └── Overrides: _get_template_name, _get_report_data,
                   _write_table_data, _get_header_footer_data
```

**Golden Rule:** Child modules only touch Hook Methods. Private pipeline
methods must never be overridden — doing so breaks the processing guarantee.

---

## 3. Module Structure

```
base_excel_report/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   └── base_excel_report.py      ← Core framework (all logic lives here)
├── views/
│   └── base_excel_report_views.xml   ← Base wizard form (two-state UI)
└── security/
    └── ir.model.access.csv
```

Child module (example — lives in a separate Odoo addon):

```
sale_excel_report/
├── __manifest__.py
├── __init__.py
├── wizard/
│   ├── __init__.py
│   └── wizard_sale_excel_report.py   ← 30–50 lines of business logic
└── views/
    └── wizard_sale_excel_report_views.xml  ← Inherits base form, adds filters
```

---

## 4. Installation & Dependencies

### Python Dependency

```bash
pip install openpyxl
```

The `openpyxl` library is the sole third-party dependency. It provides
read/write access to `.xlsx` workbooks without requiring Microsoft Excel
to be installed on the server.

> **Why not xlsxwriter or pandas?**  
> See [Section 14 — Choosing the Right Library](#14-choosing-the-right-library).

### Odoo Manifest Dependency

In child module `__manifest__.py`:

```python
'depends': ['base_excel_report'],
```

### Verify Installation

```python
# In an Odoo shell session:
import openpyxl
print(openpyxl.__version__)   # e.g. 3.1.2
```

---

## 5. Template Design Contract

A template is a standard `.xlsx` file created in Microsoft Excel and uploaded
to Odoo as an `ir.attachment` record. It must follow these conventions:

### 5.1 `TABLE_START` Marker

Place the exact string `<TABLE_START>` (angle brackets, uppercase, no spaces)
in the **leftmost column** of the **first data row** of the table.

```
Row 5 │  [A5: <TABLE_START>]  [B5: ]  [C5: ]  [D5: ]
```

- The framework scans the entire sheet cell by cell until it finds this string.
- The found cell's `(row, column)` becomes the anchor for all data insertion.
- After data is written, the marker string is overwritten by the first data
  value of the first record.
- Only **one** `<TABLE_START>` marker should exist per sheet.

### 5.2 Placeholder Syntax

Place `{{KEY}}` strings anywhere in the sheet (header area, footer area,
title cells) to inject dynamic values.

```
Cell A1:  {{COMPANY_NAME}}
Cell A3:  Report printed on: {{PRINT_DATE}}  by {{CREATOR}}
```

Rules:
- Delimiters are `{{` and `}}` — no spaces inside.
- Keys are **case-sensitive**: `{{Date}}` ≠ `{{DATE}}`.
- A placeholder can be embedded within a longer string (partial replacement).
- Multiple placeholders in one cell are all replaced.
- If the replacement string begins with `=`, Excel treats the result as a
  live formula.

### 5.3 Grand Total Row

Place a Grand Total row **below** the `<TABLE_START>` row.  
Use a placeholder (e.g. `{{GRAND_TOTAL}}`) in the amount column.

```
Row 5  │  <TABLE_START>  │  data...
Row 6  │  GRAND TOTAL    │  {{GRAND_TOTAL}}   ← this row
Row 7  │  Approved by:   │  ___________
```

When the framework calls `insert_rows()`, this row is automatically pushed
downward by exactly `total_records - 1` positions. Its own cell styles
(bold font, thick border, background color) are preserved by openpyxl's
row-push mechanism.

### 5.4 Column-Level Formatting (Fast Mode)

For reports that may exceed the Fast Mode threshold (default: 1 000 rows),
define number formatting at the **column level** in Excel instead of on
individual cells:

1. Click the column letter header (e.g. **C**) to select the entire column.
2. Right-click → **Format Cells**.
3. Set Number / Currency / Date format as required.
4. Save the template.

All cells inserted by `insert_rows()` automatically inherit the column-level
format. Python code does not need to set `number_format` on each cell.

> **Important:** Column-level formatting and cell-level formatting coexist.
> Cell-level formatting always wins (see Section 5.5).

### 5.5 Header & Grand Total Override

Even when column-level formatting is applied to the entire column, header
cells and the Grand Total row should retain their own distinct styling:

**For Header cells (rows above `<TABLE_START>`):**

1. Select the header cell range (e.g. C1:C4).
2. Right-click → **Format Cells** → Choose **General** or **Text**.
3. Apply bold, background color, and other desired styles.

Excel's cell-level format overrides the column-level format for these cells.
The framework never touches header cells, so they are safe.

**For the Grand Total row:**

The Grand Total row already carries its own cell-level formatting (bold,
double top border, etc.) applied in the template. When `insert_rows()` pushes
it downward, openpyxl preserves those styles intact at the new position.

### 5.6 Uploading the Template

```
Odoo Menu:
  Settings → Technical → Database Structure → Attachments → Create
```

| Field | Value |
|---|---|
| **Name** | Must match the string returned by `_get_template_name()` exactly (case-sensitive, including `.xlsx` extension). Example: `template_sale_report.xlsx` |
| **Attachment Type** | File |
| **File** | Upload the `.xlsx` template file |

> **Version Management Tip:**  
> To update a template, locate the existing attachment record, open it, and
> upload a new file. The Name must remain unchanged. All existing report
> wizard instances will use the updated template on their next run.

---

## 6. Processing Pipeline

The full sequence executed by `action_generate_excel()` every time the user
clicks **Generate Report**:

```
┌─────────────────────────────────────────────────────────────────────┐
│  action_generate_excel()                                            │
│                                                                     │
│  Step 1  _load_template()                                           │
│           ir.attachment → base64 decode → BytesIO → openpyxl.load  │
│                                                                     │
│  Step 2  _find_table_marker()                                       │
│           Scan all cells → find '<TABLE_START>' → (row, col)       │
│                                                                     │
│  Step 3  _get_report_data()          [HOOK]                         │
│           Child returns Recordset or list[dict]                     │
│           total_records = len(data)                                 │
│                                                                     │
│  Step 4  Determine mode                                             │
│           is_fast_mode = (total_records >= FAST_MODE_THRESHOLD)     │
│                                                                     │
│  Step 5  sheet.insert_rows(start_row + 1, amount = total - 1)      │
│           Pushes all content below marker downward                  │
│                                                                     │
│  Step 6  _copy_row_styles()          [Normal Mode only]             │
│           Deep-copy font/border/fill/alignment/number_format        │
│           from marker row → each inserted row                       │
│                                                                     │
│  Step 7  _write_table_data()         [HOOK]                         │
│           Child assigns .value (and optionally .number_format)      │
│           to each cell in the data range                            │
│                                                                     │
│  Step 8  _get_header_footer_data()   [HOOK]                         │
│           Child returns { '{{KEY}}': 'value', ... }                 │
│           _replace_placeholders() scans full sheet and substitutes  │
│                                                                     │
│  Step 9  _autofit_columns()          [Normal Mode only]             │
│           Measure max char length per column within data range      │
│           Widen if calculated width > current template width        │
│                                                                     │
│  Step 10 _export_file()                                             │
│           workbook → BytesIO → base64 → excel_file field            │
│           state → 'download'                                        │
│           Return act_window to reload wizard                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Hook Methods Reference

### 7.1 Required Hooks

All three must be overridden. The base implementation raises
`NotImplementedError` to produce a clear error message during development.

---

#### `_get_template_name() → str`

Return the exact `ir.attachment` name of the Excel template file.

```python
def _get_template_name(self):
    return 'template_sale_report.xlsx'
```

| | |
|---|---|
| Called from | `_load_template()` and `_get_output_filename()` |
| Return type | `str` — filename including `.xlsx` extension |
| Must be unique | No, but multiple reports using the same template is unusual |

---

#### `_get_report_data() → Recordset | list[dict]`

Return the complete dataset for the report. The framework calls `len()` on
the result to determine how many rows to insert.

**Flat report (Recordset):**

```python
def _get_report_data(self):
    domain = [('state', 'in', ['sale', 'done'])]
    if self.date_from:
        domain.append(('date_order', '>=', self.date_from))
    if self.date_to:
        domain.append(('date_order', '<=', self.date_to))
    return self.env['sale.order'].search(domain, order='date_order asc')
```

**Grouped report (list of dicts):**

```python
def _get_report_data(self):
    # Each dict element = one physical Excel row
    # 'subtotal' rows are counted in len() — they consume a row
    lines = []
    for rec in records:
        lines.append({'row_type': 'data', 'record': rec})
    lines.append({'row_type': 'subtotal', 'label': 'Group Total'})
    return lines
```

| | |
|---|---|
| Called from | `action_generate_excel()` — Step 3 |
| Return type | `Recordset` or `list[dict]` — must support `len()` |
| Empty result | Raises `UserError` automatically — no data guard needed in child |

---

#### `_write_table_data(sheet, data, start_row, start_col)`

Map dataset values to Excel cell coordinates. Called after rows are inserted
(and styled in Normal Mode), so cells already have the correct visual format.

```python
def _write_table_data(self, sheet, data, start_row, start_col):
    # Safe to assign number_format here even in Fast Mode (string assignment)
    FMT_DATE   = 'DD/MM/YYYY'
    FMT_NUMBER = '#,##0.00'

    for idx, rec in enumerate(data):
        row = start_row + idx

        sheet.cell(row=row, column=start_col    ).value = rec.name

        d = sheet.cell(row=row, column=start_col + 1)
        d.value         = rec.date_order.date()
        d.number_format = FMT_DATE

        a = sheet.cell(row=row, column=start_col + 2)
        a.value         = rec.amount_total
        a.number_format = FMT_NUMBER
```

**Injecting row-level formulas:**

```python
from openpyxl.utils import get_column_letter

qty_col   = get_column_letter(start_col)
price_col = get_column_letter(start_col + 1)

# Cell at (row, start_col + 2) will contain a live Excel formula
sheet.cell(row=row, column=start_col + 2).value = (
    f'={qty_col}{row}*{price_col}{row}'
)
```

| | |
|---|---|
| Called from | `action_generate_excel()` — Step 7 |
| `sheet` | `openpyxl.worksheet.worksheet.Worksheet` — active sheet |
| `data` | Exactly what `_get_report_data()` returned |
| `start_row` | 1-based integer — row index of `<TABLE_START>` |
| `start_col` | 1-based integer — column index of `<TABLE_START>` |

### 7.2 Optional Hooks

---

#### `_get_header_footer_data(start_row, end_row, start_col) → dict`

Return a dictionary mapping placeholder strings to replacement values.
Called after data is written, so `start_row` and `end_row` reflect the
final positions of the data rows in the output sheet.

```python
from openpyxl.utils import get_column_letter

def _get_header_footer_data(self, start_row, end_row, start_col):
    total_col = get_column_letter(start_col + 2)   # e.g. 'D'
    return {
        '{{COMPANY_NAME}}': self.env.company.name,
        '{{PRINT_DATE}}'  : fields.Date.today().strftime('%d/%m/%Y'),
        '{{CREATOR}}'     : self.env.user.name,
        # Inject a live Grand Total formula — SUBTOTAL skips nested SUBTOTALs
        '{{GRAND_TOTAL}}' : f'=SUBTOTAL(9,{total_col}{start_row}:{total_col}{end_row})',
    }
```

| | |
|---|---|
| Default return | `{}` — no replacements applied |
| Formula injection | Any value starting with `=` becomes a live Excel formula |
| `start_row` / `end_row` | Use these to build range-aware Excel formulas |

---

#### `_get_output_filename() → str`

Return the filename presented to the user for download.

```python
def _get_output_filename(self):
    date_str = fields.Date.today().strftime('%Y%m%d')
    return f'Sale_Report_{date_str}.xlsx'
```

| | |
|---|---|
| Default behavior | Strips `template_` prefix, appends `_output` |
| Must end with | `.xlsx` |

---

## 8. Performance Modes

### 8.1 Normal Mode

**Activated when:** `total_records < FAST_MODE_THRESHOLD` (default 1 000)

Full pipeline runs:
- `_copy_row_styles()`: Deep-copies `Font`, `Border`, `Fill`, `Alignment`,
  and `number_format` from the marker row to every inserted row.
  Ensures visual consistency (borders, colors, font weight) across all
  data rows without any work in the child module.
- `_autofit_columns()`: Measures the longest cell value in each column
  within the data range and widens columns accordingly. Prevents `###`
  truncation errors.

**Recommended for:** Presentation reports, legally significant documents,
reports with rich formatting and typically under 2 000 rows.

### 8.2 Fast Mode

**Activated when:** `total_records >= FAST_MODE_THRESHOLD`

Skipped operations:
- `_copy_row_styles()` — Eliminated. Per-cell deep-copy of style objects
  is the primary CPU/RAM bottleneck for large datasets.
- `_autofit_columns()` — Eliminated. Column-width measurement over thousands
  of rows adds significant iteration time.

Not skipped:
- `sheet.insert_rows()` — Still called. For very large datasets, combine
  Fast Mode with the "Footer-above-data" template layout
  (see [Section 8.2 continued](#fast-mode-template-layout-tip)) to minimize
  the cost of pushing rows downward.
- `number_format` assignment inside `_write_table_data()` — Still safe and
  recommended. Assigning a string to `cell.number_format` is a pure Python
  string operation with negligible cost even at 100 000 rows.

**Compensated by:**
- Column-level formatting on the template file (see Section 5.4).
- `number_format` assignment per cell in `_write_table_data()`.

**Fast Mode Template Layout Tip:**

To further reduce `insert_rows()` overhead on very large datasets, move the
Grand Total, signature area, and all footer content **above** the
`<TABLE_START>` row in the template. The data table then starts mid-sheet
with nothing below it. `insert_rows()` has no rows to push downward,
achieving maximum insertion speed.

```
Row 1-4  : Company header, title, dates  (above table)
Row 5    : Grand Total / signature area  (above table)
Row 6    : Column headers                (above table)
Row 7    : <TABLE_START>                 (data rows flow downward into empty space)
```

### 8.3 Tuning the Threshold

The constant `FAST_MODE_THRESHOLD` is defined at module level in
`base_excel_report.py`:

```python
FAST_MODE_THRESHOLD = 1000
```

Adjust based on:

| Factor | Lower Threshold | Higher Threshold |
|---|---|---|
| Server RAM | < 4 GB | ≥ 8 GB |
| Report has many columns | Yes (more style objects) | No |
| Template row has complex borders/fills | Yes | No |
| Acceptable user wait time | < 5 seconds | < 30 seconds |

Typical production values range from **500 to 2 000**.

---

## 9. Group & Subtotal Reports

### 9.1 Data Flattening Pattern

Reports requiring subtotals (grouped by partner, product category, salesperson,
etc.) use the **data flattening** strategy: `_get_report_data()` returns a
flat list where subtotal rows are interleaved with data rows.

Each element in the list is a dict with a `row_type` key:

```python
def _get_report_data(self):
    # Critical: sort by the grouping field first
    records = self.env['sale.order'].search(
        [], order='partner_id asc, date_order asc'
    )

    lines           = []
    current_partner = None

    for rec in records:
        if current_partner and current_partner != rec.partner_id:
            # Emit subtotal for the completed group
            lines.append({
                'row_type': 'subtotal',
                'label'   : f'Subtotal — {current_partner.name}',
            })

        lines.append({'row_type': 'data', 'record': rec})
        current_partner = rec.partner_id

    # Final group subtotal (after the loop ends)
    if current_partner:
        lines.append({
            'row_type': 'subtotal',
            'label'   : f'Subtotal — {current_partner.name}',
        })

    return lines
    # len(lines) = data_rows + subtotal_rows
    # Base module inserts exactly this many rows
```

In `_write_table_data()`, branch on `row_type`:

```python
def _write_table_data(self, sheet, data, start_row, start_col):
    from openpyxl.styles import Font
    from openpyxl.utils  import get_column_letter

    bold            = Font(bold=True)
    total_col_l     = get_column_letter(start_col + 2)
    current_row     = start_row
    group_start_row = start_row

    for line in data:
        if line['row_type'] == 'data':
            rec = line['record']
            sheet.cell(row=current_row, column=start_col    ).value = rec.name
            sheet.cell(row=current_row, column=start_col + 1).value = rec.partner_id.name
            amt = sheet.cell(row=current_row, column=start_col + 2)
            amt.value         = rec.amount_total
            amt.number_format = '#,##0.00'

        elif line['row_type'] == 'subtotal':
            lbl       = sheet.cell(row=current_row, column=start_col + 1)
            lbl.value = line['label']
            lbl.font  = bold

            sub       = sheet.cell(row=current_row, column=start_col + 2)
            sub.value = (
                f'=SUBTOTAL(9,'
                f'{total_col_l}{group_start_row}:{total_col_l}{current_row - 1})'
            )
            sub.font          = bold
            sub.number_format = '#,##0.00'

            # Advance group anchor to the row after this subtotal
            group_start_row = current_row + 1

        current_row += 1
```

### 9.2 SUBTOTAL vs SUM — Avoiding Double Count

When a Grand Total row spans a range that contains embedded group subtotal
rows, using `=SUM(D10:D100)` will count each value twice — once from the
data row and once from the subtotal row.

**Solution:** Use `=SUBTOTAL(9, range)` for **both** group subtotals and
the Grand Total.

Excel's `SUBTOTAL` function automatically ignores other cells in the range
that also contain `SUBTOTAL`, regardless of nesting depth.

```
Data row 1         100.00   ← counted once
Data row 2         200.00   ← counted once
Group Subtotal     =SUBTOTAL(9, D10:D11)  = 300.00   ← IGNORED by Grand Total
Data row 3         150.00   ← counted once
Data row 4          50.00   ← counted once
Group Subtotal     =SUBTOTAL(9, D13:D14)  = 200.00   ← IGNORED by Grand Total
Grand Total        =SUBTOTAL(9, D10:D14)  = 500.00   ✓ Correct
```

`SUBTOTAL` function code reference (first argument):

| Code | Function |
|---|---|
| 9 | SUM |
| 1 | AVERAGE |
| 2 | COUNT |
| 4 | MAX |
| 5 | MIN |

---

## 10. Row-Level Formulas

To insert an Excel formula into each data row (e.g. `Subtotal = Qty × Price`),
build the formula string dynamically inside the loop in `_write_table_data()`.

```python
from openpyxl.utils import get_column_letter

def _write_table_data(self, sheet, data, start_row, start_col):
    qty_col_l   = get_column_letter(start_col)         # e.g. 'B'
    price_col_l = get_column_letter(start_col + 1)     # e.g. 'C'
    # Column start_col + 2 ('D') will receive the formula

    for idx, rec in enumerate(data):
        row = start_row + idx

        sheet.cell(row=row, column=start_col    ).value = rec.product_uom_qty
        sheet.cell(row=row, column=start_col + 1).value = rec.price_unit

        formula_cell = sheet.cell(row=row, column=start_col + 2)
        formula_cell.value         = f'={qty_col_l}{row}*{price_col_l}{row}'
        formula_cell.number_format = '#,##0.00'
        # e.g. at row 10: '=B10*C10', at row 11: '=B11*C11', etc.
```

**Benefits of formula cells over pre-computed values:**

- If the user edits a quantity in the downloaded file, subtotals and grand
  totals update automatically.
- All Excel function types are supported: `IF`, `VLOOKUP`, `ROUND`,
  `IFERROR`, conditional formulas, etc.
- The cell's `number_format` controls display; the formula produces the value.

---

## 11. Creating a Child Module — Step-by-Step

### 11.1 Python Model

```python
# wizard/wizard_my_excel_report.py
# -*- coding: utf-8 -*-

from odoo            import models, fields
from openpyxl.utils  import get_column_letter


class MyExcelReport(models.TransientModel):

    _name        = 'my.excel.report'
    _inherit     = 'base.excel.report'
    _description = 'My Custom Excel Report'

    # ── Filter fields ──────────────────────────────────────────────────────
    date_from = fields.Date(string='From Date')
    date_to   = fields.Date(string='To Date')

    # ── Hook 1 (Required) ──────────────────────────────────────────────────
    def _get_template_name(self):
        return 'template_my_report.xlsx'

    # ── Hook 2 (Required) ──────────────────────────────────────────────────
    def _get_report_data(self):
        domain = []
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        return self.env['my.model'].search(domain, order='date asc')

    # ── Hook 3 (Required) ──────────────────────────────────────────────────
    def _write_table_data(self, sheet, data, start_row, start_col):
        for idx, rec in enumerate(data):
            row = start_row + idx
            sheet.cell(row=row, column=start_col    ).value = rec.name
            sheet.cell(row=row, column=start_col + 1).value = rec.date
            amt = sheet.cell(row=row, column=start_col + 2)
            amt.value         = rec.amount
            amt.number_format = '#,##0.00'

    # ── Hook 4 (Optional) ──────────────────────────────────────────────────
    def _get_header_footer_data(self, start_row, end_row, start_col):
        amt_col = get_column_letter(start_col + 2)
        return {
            '{{COMPANY}}'     : self.env.company.name,
            '{{DATE}}'        : fields.Date.today().strftime('%d/%m/%Y'),
            '{{GRAND_TOTAL}}' : f'=SUBTOTAL(9,{amt_col}{start_row}:{amt_col}{end_row})',
        }

    # ── Hook 5 (Optional) ──────────────────────────────────────────────────
    def _get_output_filename(self):
        return f"My_Report_{fields.Date.today().strftime('%Y%m%d')}.xlsx"
```

### 11.2 View Inheritance

```xml
<!-- views/wizard_my_excel_report_views.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_my_excel_report_form" model="ir.ui.view">
        <field name="name">my.excel.report.form</field>
        <field name="model">my.excel.report</field>
        <field name="inherit_id" ref="base_excel_report.view_base_excel_report_form"/>
        <field name="arch" type="xml">
            <!-- Inject filter fields into the named slot in the base view -->
            <group name="filter_area" position="inside">
                <field name="date_from"/>
                <field name="date_to"/>
            </group>
        </field>
    </record>

    <record id="action_my_excel_report" model="ir.actions.act_window">
        <field name="name">My Excel Report</field>
        <field name="res_model">my.excel.report</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
</odoo>
```

### 11.3 Manifest

```python
# __manifest__.py
{
    'name'    : 'My Excel Report',
    'version' : '16.0.1.0.0',
    'depends' : ['base_excel_report', 'my_base_module'],
    'data'    : [
        'security/ir.model.access.csv',
        'views/wizard_my_excel_report_views.xml',
    ],
}
```

---

## 12. Module-Level Constants

Defined at the top of `base_excel_report.py`. Modify these to tune framework
behaviour across all child modules simultaneously.

| Constant | Default | Description |
|---|---|---|
| `TABLE_START_MARKER` | `'<TABLE_START>'` | Exact string to scan for in template cells |
| `FAST_MODE_THRESHOLD` | `1000` | Row count at which Fast Mode activates |
| `MAX_COLUMN_WIDTH` | `50` | Maximum auto-fit column width in character units |
| `COLUMN_WIDTH_FONT_FACTOR` | `1.2` | Character-count multiplier for width calculation |
| `COLUMN_WIDTH_PADDING` | `2` | Extra width units added for visual padding |

---

## 13. Error Reference

| `UserError` Message | Root Cause | Resolution |
|---|---|---|
| `Template file '...' was not found in Attachments` | `ir.attachment.name` does not match `_get_template_name()` return value | Verify exact name including case and `.xlsx` extension |
| `Failed to read the Excel template '...'` | Uploaded file is corrupt, password-protected, or not `.xlsx` format (e.g. `.xls`) | Re-save file as `.xlsx` in Excel and re-upload |
| `Marker '<TABLE_START>' was not found` | Marker missing, misspelled, or has surrounding spaces in the cell | Open template, locate the cell, ensure value is exactly `<TABLE_START>` |
| `No records found for the selected criteria` | `_get_report_data()` returned an empty collection | Adjust date/filter parameters or verify source model data |
| `_get_template_name() must be implemented` | Child module forgot to override the hook | Add the method override to the child class |
| `_get_report_data() must be implemented` | Child module forgot to override the hook | Add the method override to the child class |
| `_write_table_data() must be implemented` | Child module forgot to override the hook | Add the method override to the child class |

---

## 14. Choosing the Right Library

### 14.1 openpyxl (This Framework)

| | |
|---|---|
| **Can read existing files** | ✅ Yes |
| **Can modify existing files** | ✅ Yes (template-based workflow) |
| **Performance** | ⚠️ Moderate (pure Python) |
| **Suitable row range** | Up to ~10 000 with Fast Mode |
| **Use case** | Presentation reports, legal documents, branded output |

### 14.2 xlsxwriter

| | |
|---|---|
| **Can read existing files** | ❌ No — write-only |
| **Can modify existing files** | ❌ No |
| **Performance** | ✅ Excellent |
| **Suitable row range** | 1 000 000+ |
| **Use case** | Raw data export, large analytical dumps, no template needed |

> Using `xlsxwriter` requires abandoning the template-based design entirely.
> All borders, colors, logos, and layout must be coded in Python explicitly.

### 14.3 pandas

| | |
|---|---|
| **Can read existing files** | ⚠️ Partial (data only, loses styles) |
| **Can modify existing files** | ❌ Cannot inject into a styled template |
| **Performance** | ✅ Excellent for data processing; depends on engine for write |
| **Suitable row range** | Millions (in-memory DataFrame) |
| **Use case** | Data transformation, pivot calculation; pairs with xlsxwriter for output |

> `pandas.DataFrame.to_excel()` uses `openpyxl` or `xlsxwriter` internally.
> It outputs a plain grid starting from cell A1 — no template injection.

### 14.4 Recommended Hybrid Strategy

| Report Type | Volume | Recommended Approach |
|---|---|---|
| Branded, formatted, printable | < 2 000 rows | `openpyxl` + this framework (Normal Mode) |
| Branded, formatted, printable | 2 000–20 000 rows | `openpyxl` + this framework (Fast Mode) |
| Raw data export, no styling | Any volume | `xlsxwriter` (separate utility function) |
| Analytical pivot / BI export | > 50 000 rows | `xlsxwriter` writes raw sheet; Excel Pivot Table does grouping |

---

## 15. Quick Reference Card

### Hook Methods

| Method | Required | Signature | Returns |
|---|---|---|---|
| `_get_template_name` | ✅ | `(self)` | `str` |
| `_get_report_data` | ✅ | `(self)` | `Recordset \| list[dict]` |
| `_write_table_data` | ✅ | `(self, sheet, data, start_row, start_col)` | `None` |
| `_get_header_footer_data` | ⬜ | `(self, start_row, end_row, start_col)` | `dict[str, str]` |
| `_get_output_filename` | ⬜ | `(self)` | `str` |

### Performance Mode Summary

| | Normal Mode | Fast Mode |
|---|---|---|
| **Trigger** | `records < 1000` | `records >= 1000` |
| `_copy_row_styles()` | ✅ Runs | ❌ Skipped |
| `_autofit_columns()` | ✅ Runs | ❌ Skipped |
| `number_format` in child | Optional | **Recommended** |
| Template column formatting | Optional | **Required** |

### Template Checklist

```
□  <TABLE_START> in leftmost cell of first data row
□  {{PLACEHOLDERS}} placed in header / footer cells
□  {{GRAND_TOTAL}} in the amount cell of the Grand Total row
   (Grand Total row must be BELOW <TABLE_START> in the template)
□  Column-level number/date formatting applied (for Fast Mode reports)
□  Header cells explicitly formatted as General/Text to override column format
□  Grand Total row styled with bold/border (styles are preserved by insert_rows)
□  File saved as .xlsx (not .xls or .xlsm)
□  Uploaded to ir.attachment with Name matching _get_template_name() exactly
```

### Common Formula Strings

```python
# Currency — Vietnamese locale
'#,##0'       # 1,500,000
'#,##0.00'    # 1,500,000.00

# Date
'DD/MM/YYYY'  # 31/07/2026

# Percentage
'0.00%'       # 12.50%

# Group subtotal (avoids double count in Grand Total)
f'=SUBTOTAL(9,{col}{group_start}:{col}{current_row - 1})'

# Grand Total (ignores nested SUBTOTAL rows)
f'=SUBTOTAL(9,{col}{start_row}:{col}{end_row})'

# Row-level formula
f'={qty_col}{row}*{price_col}{row}'

# Conditional formula
f'=IF({qty_col}{row}>10,"Bulk","Standard")'
```

---

*For questions, bug reports, or feature requests, open an issue in your
project repository or contact the module maintainer.*
