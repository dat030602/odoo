# dn_excel_template_report — Pixel-Perfect Excel Template Reporting Engine for Odoo 19

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67.svg)](https://www.odoo.com)
[![Python Version](https://img.shields.io/badge/Python-3.12-3776AB.svg)](https://www.python.org)
[![Engine](https://img.shields.io/badge/Engine-openpyxl_3.1+-017E84.svg)](https://openpyxl.readthedocs.io)
[![License](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Test Coverage](https://img.shields.io/badge/Tests-100%25_Passing-brightgreen.svg)]()

`dn_excel_template_report` is a modular, high-fidelity Excel report generation module for **Odoo 19.0** (Community and Enterprise editions). It allows system administrators and business users to design professional reports visually in Microsoft Excel (`.xlsx`), upload them as templates, and bind them directly to the native Odoo **Print** menu.

When printing, the engine dynamically renders Odoo record data into the template while **strictly preserving** original formatting: font styles, borders, cell fills, merged cells, row heights, conditional formatting rules, images, and Excel formulas.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Architecture & Directory Structure](#architecture--directory-structure)
   - [Architectural Layers](#architectural-layers)
   - [Directory Layout](#directory-layout)
   - [Processing Engine Services (`services/`)](#processing-engine-services-services)
3. [Template Syntax Guide](#template-syntax-guide)
   - [Scalar Placeholders (`${...}`)](#1-scalar-placeholders-)
   - [Table Loop Rows (`${table:...}`)](#2-table-loop-rows-table)
   - [Embedded Images (`${image:...}`)](#3-embedded-images-image)
   - [Evaluation Context & Helper Functions](#4-evaluation-context--helper-functions)
4. [Section 7.2 Layout Engine & Formula Expansion](#section-72-layout-engine--formula-expansion)
   - [The Bottom-Up Row Expansion Principle](#the-bottom-up-row-expansion-principle)
   - [Delta ($\Delta$) Calculation](#delta-delta-calculation)
   - [Openpyxl Technical Quirks & Mitigations](#openpyxl-technical-quirks--mitigations)
   - [Formula Translation & Range Boundary Expansion](#formula-translation--range-boundary-expansion)
   - [Section 7.2 Reference Fixture Walkthrough ($N = 3$)](#section-72-reference-fixture-walkthrough-n--3)
   - [Edge Cases ($N = 1$, $N = 0$, $N = 200$)](#edge-cases-n--1-n--0-n--200)
5. [Setup, Configuration & User Guide](#setup-configuration--user-guide)
   - [Installation](#installation)
   - [Creating a Report Template](#creating-a-report-template)
   - [Defining Custom Variables](#defining-custom-variables)
   - [Configuring Datasources & Columns](#configuring-datasources--columns)
   - [Binding to Native Print Action Menu](#binding-to-native-print-action-menu)
   - [Single Record vs. Multi-Record Batch ZIP Export](#single-record-vs-multi-record-batch-zip-export)
   - [Template Validation & Test Print](#template-validation--test-print)
6. [Security & Multi-Company Isolation](#security--multi-company-isolation)
7. [Automated Test Suite Execution](#automated-test-suite-execution)
   - [Standalone Layout Unit Tests](#1-standalone-layout-unit-tests-pure-python-312)
   - [Odoo ORM Integration Tests](#2-odoo-orm-integration-tests-transactioncase)
   - [Odoo CLI Module Upgrade & Verification](#3-odoo-cli-module-upgrade--verification)
8. [Technical Specifications](#technical-specifications)
9. [License & Support](#license--support)

---

## Key Features

- **Pixel-Perfect Fidelity**: Upload standard `.xlsx` files designed in Excel. Original typography, color fills, number formatting, borders, and column widths are 100% maintained.
- **Zero-ORM Core Processing Engine**: The rendering core in `services/` operates independently on in-memory `openpyxl.Workbook` instances, enabling lightning-fast rendering and unit testing without server overhead.
- **Section 7.2 Layout Engine**: Sophisticated row expansion algorithm that duplicates template rows, shifts downstream rows, clones merged cell ranges, shifts conditional formatting boundaries, and maintains exact row heights.
- **Intelligent Formula Translation**:
  - Translates relative cell coordinates inside duplicated loop rows (e.g. `=F19*H19` &rarr; `=F20*H20` &rarr; `=F21*H21`) using `openpyxl.formula.translate.Translator`.
  - Expands summary aggregation ranges spanning the loop row (e.g. `=SUM(I19:I19)` &rarr; `=SUM(I19:I21)`).
  - Preserves absolute coordinate references (e.g. `$H$2`).
  - Sets `wb.calculation.fullCalcOnLoad = True` so Microsoft Excel automatically recalculates all formulas upon opening.
- **Proportional Image Insertion**: Embeds binary, base64, or data URL images (e.g. product photos, company logos, digital signatures) proportionally scaled inside cell or merged cell boundaries with automatic 4% margin padding.
- **Dynamic Print Action Binding**: One-click binding to Odoo's native Action / Print menu on target models via `ir.actions.server`. No custom XML actions or Python code required per model.
- **Single & Multi-Record ZIP Export**: Print a single record to download `.xlsx` directly, or select multiple records in List View to download a consolidated `.zip` archive containing individual `.xlsx` reports.
- **Two Configuration Modes**: Use the no-code builder for variables and data sources, or use Python Code mode for advanced calculations with a controlled module whitelist.
- **Odoo 19 Native Architecture**: Adheres strictly to Odoo 19 design principles: `<list>` views, `<chatter/>` components, direct XML modifiers (`invisible="..."`, `readonly="..."`), `models.Constraint`, and `res.groups.privilege`.

---

## Architecture & Directory Structure

### Architectural Layers

The module is structured into four distinct, decoupled layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   1. Presentation & Config Layer                      │
│   (models/template.py, models/variable.py, models/datasource.py)       │
│   - Stores template file (.xlsx attachment) and metadata               │
│   - Configures custom variables and table loop datasources             │
│   - Dynamic binding to ir.actions.server ('Print: <Name>')            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Record data & raw .xlsx bytes
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 2. Pure-Python Processing Engine                       │
│        (services/renderer.py, layout.py, formula.py, etc.)             │
│   - Zero ORM dependency: operates on openpyxl.Workbook and dicts/objs  │
│   - Token scanning (${...}, ${table:...}, ${image:...})                │
│   - Bottom-up row expansion, merge restoration, CF shifting            │
│   - Relative formula translation and range boundary expansion          │
│   - Proportional image embedding and fullCalcOnLoad activation         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Rendered .xlsx PKZip bytes
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      3. Delivery / HTTP Layer                          │
│                      (controllers/main.py)                             │
│   - Route: /excel_template_report/download (auth='user')               │
│   - Resolves dynamic filename via filename_expr                        │
│   - Streams single .xlsx or packages multi-record .zip archive         │
└────────────────────────────────────────────────────────────────────────┘
```

### Directory Layout

```
/opt/odoo19/dev/dn_excel_template_report/
├── __init__.py                      # Package root: imports models, controllers, services
├── __manifest__.py                  # Odoo 19 module manifest and metadata
├── controllers/
│   ├── __init__.py
│   └── main.py                      # HTTP download controller (/excel_template_report/download)
├── models/
│   ├── __init__.py
│   ├── datasource.py                # Models: excel.report.datasource, excel.report.datasource.column
│   ├── template.py                  # Model: excel.report.template (validation, binding, rendering)
│   └── variable.py                  # Model: excel.report.variable (custom runtime expressions)
├── security/
│   ├── ir.model.access.csv          # Granular ACL rules for all models
│   └── ir.model.security.xml        # Security group definition and multi-company record rules
├── services/
│   ├── __init__.py
│   ├── evaluator.py                 # safe_eval sandbox evaluation and rich context builder
│   ├── formula.py                   # Relative formula translation and summary range expansion
│   ├── images.py                    # Bounding box calculation, image scaling, and embedding
│   ├── layout.py                    # Section 7.2 bottom-up row expansion and metadata restoration
│   ├── parser.py                    # Regex scanner, token classification, and template validation
│   ├── renderer.py                  # Master pipeline coordinator
│   └── resolver.py                  # Dot-path traversal, aliases, and openpyxl type normalization
├── static/
│   └── description/
│       ├── icon.png                 # Module icon
│       └── index.html               # Odoo App Store presentation page
├── tests/
│   ├── __init__.py                  # Imports test_layout and test_render
│   ├── fixtures/
│   │   └── TEMPLATE.xlsx                 # Section 7.2 demo fixture
│   ├── test_layout.py               # Standalone pure-Python tests for Section 7.2 layout engine
│   └── test_render.py               # Odoo TransactionCase integration tests
└── views/
    ├── menus.xml                    # Menu hierarchy (Technical > Excel Reports)
    └── template_views.xml           # Form, list, and search views (Odoo 19 syntax)
```

### Processing Engine Services (`services/`)

| Service File | Responsibilities | Core Functions |
| :--- | :--- | :--- |
| `parser.py` | Scans worksheets for `${...}` tokens; classifies into scalar `expr`, `table`, or `image`; discovers loop rows; validates that a single row does not contain conflicting datasources. | `scan_sheet(ws)`, `parse_cell(cell)`, `classify(expr)`, `validate_template_sheet(ws)` |
| `resolver.py` | Safely traverses dot-separated paths (`partner_id.name`) on Odoo recordsets or dictionaries; resolves `PATH_ALIASES` (e.g. `address` &rarr; `contact_address`); normalizes ORM values to native openpyxl types (`to_cell_value`). | `resolve_path(target, path)`, `to_cell_value(val)` |
| `evaluator.py` | Evaluates Python expressions within a safe sandbox context (`safe_eval`); supplies standard variables (`record`, `company`, `user`, `datetime`) and formatting helpers (`format_date`, `format_amount`); resolves custom variables. | `build_eval_context(...)`, `evaluate_expression(expr, context, strict)` |
| `layout.py` | Executes Section 7.2 bottom-up row expansion; calculates delta ($\Delta$); captures and shifts sheet metadata (merged cells, conditional formatting rules, row dimensions, images); duplicates cell styling; populates row data. | `expand_loop_row(ws, loop_row, count, policy)`, `fill_loop_rows(ws, loop_row, count, row_data_list)` |
| `formula.py` | Translates relative cell formulas across duplicated rows using `openpyxl.formula.translate.Translator`; tokenizes and expands summary formulas spanning loop rows (`=SUM(I19:I19)` &rarr; `=SUM(I19:I21)`); preserves absolute `$col$row` references. | `translate_cell_formula(...)`, `adjust_formula_for_shift(...)`, `adjust_all_formulas(...)` |
| `images.py` | Computes available pixel bounding box (aggregating across merged cell spans at 96 DPI); applies 4% margin padding; scales images proportionally; anchors image to cell; clears placeholder text. | `insert_image_into_cell(ws, coordinate, image_data)`, `get_cell_box_pixels(ws, coordinate)` |
| `renderer.py` | Master pipeline coordinator: loads workbook, builds context, iterates worksheets, triggers bottom-up loop expansions, embeds images, rescans scalar placeholders, activates `fullCalcOnLoad`, and outputs `.xlsx` bytes. | `render_template(template_bytes, record, ...)` |

---

## Template Syntax Guide

Templates use standard Excel cell values containing `${...}` placeholder tokens.

### 1. Scalar Placeholders (`${...}`)

Scalar placeholders evaluate single values from the Odoo record or reporting context.

```excel
${record.name}
${record.partner_id.name}
${fields.date_order}
${company.name}
${user.name}
```

#### Field Path Navigation & Aliases
- Dot-notation traverses relational fields seamlessly: `${record.partner_id.country_id.name}`.
- If any intermediate field is empty (`False` or `None`), the resolver safely stops and outputs an empty string `""`.
- Built-in aliases in `resolver.py` map common shortcuts automatically (e.g. `partner_id.address` &rarr; `partner_id.contact_address`).

#### Type Conversion Rules (`to_cell_value`)
- `False` or `None` &rarr; `""` (Empty string). **Crucial**: Odoo boolean `False` values for unset fields are rendered as blank cells in Excel, never as the text `"FALSE"`.
- `int`, `float`, `Decimal` &rarr; Native numeric value preserved in Excel (allowing Excel formulas to calculate directly).
- `date`, `datetime`, `time` &rarr; Native openpyxl date/datetime object.
- Many2one recordset &rarr; Record's `display_name`.
- One2many / Many2many recordset &rarr; Comma-separated list of `display_name` values.

#### Whole-Cell vs. Inline Substring Evaluation
- **Whole-Cell Replacement**: When a cell contains *only* a placeholder (e.g. cell value is `${record.amount_total}`):
  The cell value is replaced directly with the native typed value (e.g. numeric `1450.50`), preserving Excel numeric formatting.
- **Inline Substring Replacement**: When a cell contains mixed text (e.g. `Order Ref: ${record.name} - ${record.date_order}`):
  Placeholders are interpolated into the string.

### 2. Table Loop Rows (`${table:...}`)

Table loop placeholders designate a row in your template to be dynamically expanded for a One2many or Many2many collection (e.g. purchase order lines, invoice lines).

```excel
| A                          | B                           | C                          | I           |
|----------------------------|-----------------------------|----------------------------|-------------|
| ${table:summary.product}   | ${table:summary.order_ref}  | ${table:summary.quantity}  | =F19*H19    |
```

#### Syntax:
```excel
${table:<datasource_name>.<column_key>}
```

- `<datasource_name>`: Must match the **Datasource Name** defined in the template configuration (e.g. `summary`).
- `<column_key>`: Must match the **Column Key** defined under that datasource (e.g. `product`, `quantity`).

#### Table Loop Rules:
1. **Automatic Discovery**: The scanner scans every row in the worksheet. Any row containing one or more `${table:...}` placeholders is registered as a **Loop Row**.
2. **Single Datasource Rule**: All `${table:...}` placeholders on the same row **must belong to the same datasource**. Mixing multiple datasources on a single row (e.g. `${table:items.name}` and `${table:taxes.amount}`) raises a descriptive `TemplateError`.
3. **Loop Variables**: When evaluating column expressions for each line, the engine injects:
   - `line`: The current record line item (e.g. `purchase.order.line`).
   - `idx`: The 1-based line counter (`1`, `2`, `3`, ...).
   - Plus the full standard context (`record`, `company`, `user`, `datetime`).

### 3. Embedded Images (`${image:...}`)

Embed images dynamically into cells or merged cell ranges:

```excel
${image:record.company_id.logo}
${image:line.product_id.image_128}
${image:user.signature}
```

#### Image Processing Rules:
- Supports raw image bytes, base64 strings, and data URI strings (`data:image/png;base64,...`).
- **Bounding Box Calculation**: Calculates the exact pixel width and height available in the cell at 96 DPI.
- **Merged Cell Aggregation**: If the cell is merged (e.g. `B2:D5`), the engine sums the widths and heights of all columns and rows in the merge to compute the full merged bounding box.
- **Proportional Scaling**: Scales the image to fit completely within the box while strictly preserving the original aspect ratio.
- **Margin Padding**: Insets the image with a 4% margin padding so it does not touch cell borders.
- **Text Clearing**: Automatically clears the placeholder text `${image:...}` from the cell value so no text is visible behind the image.

### 4. Evaluation Context & Helper Functions

The evaluation environment provides a rich, secure context for Python expressions:

| Variable / Helper | Description | Example |
| :--- | :--- | :--- |
| `record` | Current primary Odoo record | `record.partner_id.name` |
| `records` | Recordset being processed | `len(records)` |
| `fields` | Alias for `record` | `fields.date_order` |
| `company` | Current company (`res.company`) | `company.currency_id.name` |
| `user` | Current user (`res.users`) | `user.name` |
| `env` | Odoo Environment (`self.env`) | `env['res.currency'].search([])` |
| `datetime` | Python `datetime` module | `datetime.datetime.now().year` |
| `date` | Python `datetime.date` class | `date.today()` |
| `format_date(val, fmt)` | Formats dates with Odoo language locale or custom format | `format_date(record.date_order, '%d/%m/%Y')` |
| `format_amount(val, curr)` | Formats monetary amounts with currency symbol | `format_amount(record.amount_total)` |
| `line` | Current line item (inside table loops) | `line.product_qty * line.price_unit` |
| `idx` | 1-based iteration counter (inside table loops) | `idx` |
| Custom Variables | Any variable defined in the **Variables** tab | `${tax_total}` |

---

## Section 7.2 Layout Engine & Formula Expansion

The layout engine (`services/layout.py` and `services/formula.py`) implements the specification defined in **Section 7.2** of the technical document.

### The Bottom-Up Row Expansion Principle

When a template contains multiple table loops on a single worksheet, expanding an upper row shifts all row coordinates below it. If processed top-to-bottom, subsequent loop rows would have shifted row numbers, corrupting cell coordinates.

**The Solution**: The engine discovers all loop rows on each worksheet and sorts them in **descending row order** (bottom-up):
```python
sorted_loop_rows = sorted(scan.loop_rows.values(), key=lambda lr: lr.row, reverse=True)
```
Lower loops expand first. Row shifts push rows below them downward, leaving all upstream loop row indices completely unaffected.

### Delta ($\Delta$) Calculation

For a loop row at row index $R$ accommodating $N$ records:

$$\Delta = \begin{cases} 
N - 1 & \text{if } N \ge 1 \\
0 & \text{if } N = 0 \text{ and policy is } \texttt{keep\_blank} \\
-1 & \text{if } N = 0 \text{ and policy is } \texttt{remove}
\end{cases}$$

- **$N \ge 1$**: Template row $R$ hosts line 1. Rows $R+1$ to $R+N-1$ are inserted (`ws.insert_rows(R + 1, amount=N - 1)`). $\Delta = N - 1$.
- **$N = 0$, `keep_blank`**: No rows inserted or deleted. $\Delta = 0$. Table placeholders on row $R$ are cleared to render a clean, blank row.
- **$N = 0$, `remove`**: Template row $R$ is deleted (`ws.delete_rows(R, amount=1)`). All downstream rows shift up by 1. $\Delta = -1$.

---

### Openpyxl Technical Quirks & Mitigations

Standard `openpyxl` has several known failure modes when manipulating rows. The layout engine implements robust mitigations:

#### 1. Slave Cell Border Annihilation (Quirk 1)
- **Problem**: Calling openpyxl's `ws.unmerge_cells(...)` destroys border styles on all "slave" cells (non-top-left cells) in the merged range.
- **Mitigation**: The engine captures all merged ranges and then clears the collection directly without unmerging:
  ```python
  saved_merges = list(ws.merged_cells.ranges)
  ws.merged_cells.ranges.clear()  # Preserves individual cell border objects!
  ```

#### 2. Merged Cell Range Shifting & Cloning (Quirk 2)
- **Template Row Merges**: If the template row contains a merge (e.g. `A19:C19`), the merge must be cloned for every duplicated row ($k = 0 \dots N-1$):
  $$\text{Add: } \text{CellRange}(min\_col=A, min\_row=R+k, max\_col=C, max\_row=R+k)$$
- **Downstream Merges**: Any merged range strictly below the loop row ($min\_row > R$) is shifted by $\Delta$:
  $$\text{Shift: } min\_row \leftarrow min\_row + \Delta, \quad max\_row \leftarrow max\_row + \Delta$$
- **Spanning Merges**: Any merged range spanning across the loop row ($min\_row \le R \le max\_row$) has its bottom boundary extended:
  $$\text{Expand: } max\_row \leftarrow max\_row + \Delta$$

#### 3. Shared Mutable StyleArray (Quirk 3)
- **Problem**: Assigning `dst._style = src._style` directly creates a shared reference. Mutating borders or font on one row corrupts all other duplicated rows.
- **Mitigation**: Explicit shallow copy:
  ```python
  dst._style = copy.copy(src._style)
  ```

#### 4. Conditional Formatting `OrderedDict` Hash Corruption (Quirk 4)
- **Problem**: Modifying `CellRange` instances in-place inside `ws.conditional_formatting._cf_rules` changes the object's hash while it is stored as a dictionary key, corrupting openpyxl's internal dictionary.
- **Mitigation**: The engine clears `_cf_rules`, computes new `CellRange` / `MultiCellRange` objects with updated row indices, and reconstructs a fresh `OrderedDict`:
  ```python
  saved_cf_rules = OrderedDict(ws.conditional_formatting._cf_rules)
  ws.conditional_formatting._cf_rules.clear()
  # Rebuild with new ConditionalFormatting(sqref=MultiCellRange(new_ranges))
  ```

#### 5. Formula Recalculation on Load (Quirk 5)
- **Problem**: Openpyxl writes raw formula strings into `.xlsx` XML but does not calculate formula results. Opening the file in Excel without recalculation can display blank or `#VALUE!` cells until clicked.
- **Mitigation**: The engine sets the calculation flag on workbook save:
  ```python
  wb.calculation.fullCalcOnLoad = True
  ```
  This instructs Microsoft Excel, LibreOffice Calc, and Apple Numbers to force a full recalculation of all formulas immediately upon opening.

---

### Formula Translation & Range Boundary Expansion

The formula service (`services/formula.py`) handles two distinct formula scenarios:

#### Scenario A: Intra-Row Relative Formulas
Formulas inside the loop row must translate their row references as rows are duplicated:
- Row 19 (Template): `=F19*H19`
- Row 20 (Duplicated): `=F20*H20`
- Row 21 (Duplicated): `=F21*H21`

This is accomplished using `openpyxl.formula.translate.Translator`:
```python
Translator(src_formula, origin="I19").translate_formula("I20")
```

#### Scenario B: Downstream Summary Formulas & Spanning Ranges
Summary formulas located below the loop row (e.g. `=SUM(I19:I19)`) must:
1. Shift their own cell location by $\Delta$ (from cell `I20` to `I22` when $\Delta = +2$).
2. Expand their range end coordinate to encompass all new rows:
   $$=SUM(I19:I19) \implies =SUM(I19:I21)$$

The engine uses `openpyxl.formula.tokenizer.Tokenizer` to parse the formula tokens:
```python
# If range start <= loop_row <= range end:
# new_start = start
# new_end = end + delta
"=SUM(I19:I19)" -> "=SUM(I19:I21)"
```

#### Scenario C: Absolute References
Any coordinate prefixed with `$` (e.g. `$H$2` or `$A$1:$D$10`) is identified by regex `CELL_REF_RE` and left untouched.

---

### Section 7.2 Reference Fixture Walkthrough ($N = 3$)

Using the demo fixture `TEMPLATE.xlsx` (Sheet `'RFQ'`):

| Element | Template Coordinate | Rendered Coordinate ($N = 3, \Delta = +2$) | Verification Details |
| :--- | :--- | :--- | :--- |
| **Loop Row 1** | Row 19 | Row 19 | Populated with Line 1 data (`Product 1`) |
| **Loop Row 2** | — (inserted) | Row 20 | Populated with Line 2 data (`Product 2`) |
| **Loop Row 3** | — (inserted) | Row 21 | Populated with Line 3 data (`Product 3`) |
| **Loop Merge** | `A19:C19` | `A19:C19`, `A20:C20`, `A21:C21` | Merged range cloned across all 3 rows |
| **Loop Formula** | `I19` (`=F19*H19`) | `I19` (`=F19*H19`), `I20` (`=F20*H20`), `I21` (`=F21*H21`) | Translated relatively |
| **Total Label** | `H20` (`Total`) | `H22` (`Total`) | Shifted down by $+2$ |
| **Summary Formula**| `I20` (`=SUM(I19:I19)`) | `I22` (`=SUM(I19:I21)`) | Shifted by $+2$ and range expanded |
| **Notes Block** | `A22:I23` (`Notes`) | `A24:I25` (`Notes`) | Merge and content shifted by $+2$ |
| **Terms Block** | `A24:I37` | `A26:I39` | Merge and content shifted by $+2$ |
| **Material Specs** | `A38:I51` | `A40:I53` | Merge and content shifted by $+2$ |
| **Signatures** | `A52` | `A54` | Shifted down by $+2$ |
| **Order Date** | `B54` (`${fields.date_order}`) | `B56` | Evaluated date value shifted by $+2$ |
| **CF Range 1** | `G19:I20` | `G19:I22` | Boundary expanded to cover loop rows + total |
| **CF Range 2** | `G22:I37` | `G24:I39` | Range shifted down by $+2$ |
| **Row Dimensions** | Height of Row 19 | Heights of 19, 20, 21 | Exact row height replicated; downstream shifted |

---

### Edge Cases ($N = 1$, $N = 0$, $N = 200$)

| Edge Case | Delta ($\Delta$) | Engine Behavior |
| :--- | :---: | :--- |
| **$N = 1$** | $0$ | **Identity Transformation**: No rows inserted or deleted. Row 19 populated directly. Total remains at Row 20 (`=SUM(I19:I19)`). Merges and CF remain at initial coordinates. |
| **$N = 0$ (`keep_blank`)** | $0$ | **Blank Template Preservation**: No rows inserted or deleted. Table placeholders on Row 19 are cleared to empty strings `""`. Total remains at Row 20 (`=SUM(I19:I19)`). |
| **$N = 0$ (`remove`)** | $-1$ | **Template Row Deletion**: Row 19 is deleted. Downstream rows shift up by 1 (Total moves to Row 19). Merges and CF shift up by $-1$. |
| **$N = 200$ (Stress Test)**| $+199$ | **High-Volume Expansion**: Rows 19 to 218 populated with 200 items. Summary formula expands to `=SUM(I19:I218)` at Row 219. Executes in **under 1.0 second**. |

---

## Setup, Configuration & User Guide

### Installation

1. Place `dn_excel_template_report` in your custom addons directory (e.g. `/opt/odoo19/dev/dn_excel_template_report`).
2. Ensure Python package `openpyxl` (version 3.1 or higher) and `Pillow` are installed in your Python environment:
   ```bash
   /opt/venv312/bin/pip install openpyxl Pillow
   ```
3. Update Odoo's module list and install the module:
   ```bash
   /opt/venv312/bin/python3.12 /opt/odoo19/odoo-bin -c /opt/odoo19.conf -d odoo19 -i dn_excel_template_report --stop-after-init
   ```

---

### Creating a Report Template

1. In Odoo, activate **Developer Mode**.
2. Navigate to: **Technical &rarr; Excel Reports &rarr; Report Templates**.
3. Click **New** to open the template form:
   - **Template Name**: Enter a human-readable title (e.g. `Purchase Order Summary`).
   - **Model**: Select the target Odoo model (e.g. `Purchase Order` &rarr; `purchase.order`).
   - **Template File (.xlsx)**: Upload your designed `.xlsx` workbook.
     - *Security Rule*: The file must be a valid OpenXML ZIP archive containing `xl/workbook.xml` and must not exceed 10 MB. Macro-enabled workbooks (`.xlsm` or files containing `xl/vbaProject.bin`) are strictly rejected.
   - **Export Filename Expression**: Python expression evaluating the exported filename without extension:
     ```python
     "'RFQ_%s_%s' % (record.name.replace('/', '_'), datetime.datetime.now().strftime('%Y%m%d'))"
     ```
   - **Empty Table Policy**:
     - `Keep 1 Blank Row`: If the collection is empty, retain the row with empty cells.
     - `Remove Row`: If the collection is empty, delete the template row and collapse the table.
   - **Allowed Groups**: Optional. Restrict report printing to specific user groups. Leave blank for all authorized users.

---

### Defining Custom Variables

Under the **Variables** notebook tab, define custom expressions evaluated before rendering:

| Sequence | Variable Name | Python Expression | Value Type |
| :---: | :--- | :--- | :---: |
| 10 | `tax_amount` | `record.amount_tax` | Number |
| 20 | `is_international` | `record.partner_id.country_id != company.country_id` | Auto |
| 30 | `lead_time_days` | `(record.date_planned - record.date_order).days if record.date_planned and record.date_order else 0` | Number |

Variables are evaluated sequentially; variables with higher sequence numbers can access variables evaluated earlier. In the Excel template, reference them as `${tax_amount}`, `${is_international}`, etc.

---

### Configuring Datasources & Columns

Under the **Data Sources** notebook tab, configure table loop mappings:

1. Click **Add a line** under Data Sources:
   - **Datasource Name**: Unique identifier matching the template `${table:<name>.<key>}` (e.g. `summary`).
   - **Rows Expression**: Python expression returning an iterable recordset:
     ```python
     record.order_line.filtered(lambda l: not l.display_type)
     ```
2. Under **Columns**, define column keys and cell expressions:

| Sequence | Column Key | Cell Expression | Description |
| :---: | :--- | :--- | :--- |
| 10 | `product` | `line.product_id.display_name` | Product name |
| 20 | `order_number`| `record.name` | Parent PO name |
| 30 | `quantity` | `line.product_qty` | Quantity ordered |
| 40 | `uom` | `line.product_uom.name` | Unit of measure |
| 50 | `price` | `line.price_unit` | Unit price |
| 60 | `item_idx` | `idx` | Line number (1, 2, 3...) |

### Python Code Mode

Use **Python Code** mode when a report needs computed values, conditional logic, or custom table rows that are not practical in the visual builder.

1. Select **Python Code** in the template form.
2. Populate `variables` and `tables` in the script, or return them through `result`.
3. Use **Excel Reports &rarr; Python Modules** to manage optional imports. Every new module starts disabled. Click **Test Module**; it is enabled only after the module imports successfully.

The script context exposes `allowed_modules` and `_dynamic_import(name)`. Imports are exact-name lookups from the whitelist. Network, filesystem, process, and unrestricted reflection modules are not included in the default safe library set. A module that is not enabled raises an error instead of being imported.

Example:

```python
json_module = _dynamic_import('json')
variables['payload'] = json_module.dumps({'reference': record.name})
```

---

### Binding to Native Print Action Menu

Once your template and datasources are configured:
1. Click the **Bind Print Action** button in the header of the template form.
2. The module dynamically generates an `ir.actions.server` bound to the target model's `Print` menu (`binding_type='report'`).
3. Open any record of the target model (e.g. a Purchase Order in **Purchase &rarr; Requests for Quotation**):
   - Click the **Print** menu at the top of the form.
   - You will see your new action: `Print: Purchase Order Summary`.
4. To remove the button at any time, simply click **Unbind Print Action** on the template.

---

### Single Record vs. Multi-Record Batch ZIP Export

- **Single Record Export**:
  - Printing from a Form View (or selecting exactly 1 record in List View) downloads the rendered `.xlsx` file directly:
  - Filename matches `filename_expr` (e.g. `RFQ_PO00014_20261020.xlsx`).
- **Multi-Record Batch Export**:
  - In List View, select multiple checkboxes (e.g. 15 RFQs) and click **Print &rarr; Print: Purchase Order Summary**.
  - The controller streams a consolidated ZIP archive: `Purchase_Order_Summary_export.zip`.
  - Inside the archive, each record is an individually rendered `.xlsx` report. Duplicate filenames are automatically suffixed (`_2`, `_3`) to prevent collisions.

---

### Template Validation & Test Print

- **Validate Template**: Click **Validate Template** on the template form. The engine parses the workbook and compares all placeholders against defined variables and datasources:
  - Highlights unknown datasources or missing column keys.
  - Warns about unmapped variable names.
  - Displays a clean success notification if all references are valid.
- **Test Print**: Click **Test Print** to immediately render and download a report using the first available record in the target model, allowing instant visual inspection of the output.

---

## Security & Multi-Company Isolation

- **Access Control List (`ir.model.access.csv`)**:
  - Standard users (`base.group_user`) have read access to templates permitted by `group_ids`.
  - System administrators and report managers (`excel_report_template_group_manager`) have full CRUD access.
- **Multi-Company Record Rules (`security/ir.model.security.xml`)**:
  - Templates can be company-specific (assigned to `company_id`) or global (`company_id = False`).
  - Standard multi-company record rules ensure users only see and execute templates belonging to their active allowed companies:
    ```xml
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]</field>
    ```
- **Permission Checking on Download**: The controller `/excel_template_report/download` checks:
  1. Active user authentication (`auth='user'`).
  2. Model-level read access to `excel.report.template`.
  3. Group authorization via `template.group_ids`.
  4. Record-level read access to all requested target records.

---

## Automated Test Suite Execution

The module includes comprehensive automated tests covering both pure-Python layout shifts and Odoo ORM integration.

### 1. Standalone Layout Unit Tests (Pure Python 3.12)

Executes directly with `openpyxl` against `tests/fixtures/TEMPLATE.xlsx` without starting the Odoo server:

```bash
/opt/venv312/bin/python3.12 -m unittest /opt/odoo19/dev/dn_excel_template_report/tests/test_layout.py
```

*Expected Output:*
```
.....
----------------------------------------------------------------------
Ran 5 tests in 0.046s

OK
```

Test coverage:
- `test_n_equals_1_no_layout_change`: Identity shift ($\Delta = 0$).
- `test_n_equals_3_matches_specification`: Section 7.2 multi-row expansion ($\Delta = +2$), merge cloning, formula translation, and CF range expansion.
- `test_n_equals_0_policy_keep_blank`: Blank row retention ($\Delta = 0$).
- `test_n_equals_0_policy_remove`: Row deletion and upward shift ($\Delta = -1$).
- `test_n_equals_200_large_batch`: High-volume 200-row stress test (< 1.0s).

---

### 2. Odoo ORM Integration Tests (`TransactionCase`)

Runs inside Odoo's test environment with automated database rollback:

```bash
/opt/venv312/bin/python3.12 /opt/odoo19/odoo-bin \
    -c /opt/odoo19.conf \
    -d odoo19 \
    -u dn_excel_template_report \
    --test-enable \
    --test-tags=dn_excel_template_report \
    --stop-after-init \
    --log-level=test
```

Test coverage:
- `test_01_template_crud_and_binding`: Model CRUD, `action_bind_print_button`, `ir.actions.server` registration, and `action_unbind_print_button`.
- `test_02_render_record_success`: End-to-end rendering on `purchase.order`, returning valid PKZip bytes.
- `test_03_invalid_file_rejection`: Rejection of corrupted files, non-Excel archives, and macro-enabled `.xlsm` files.
- `test_04_multi_company_isolation`: Multi-company record rule verification.
- `test_05_access_control`: Enforcement of `group_ids` permissions.

---

### 3. Odoo CLI Module Upgrade & Verification

Verify clean module installation and upgrade with zero errors or tracebacks:

```bash
set -a && source /opt/odoo19/.agents/.env && set +a
$ODOO_PYTHON $ODOO_BIN -c $ODOO_CONF -d $ODOO_DB -u dn_excel_template_report --stop-after-init --log-level=warn
```

*Expected Output:*
Exit code `0` with zero tracebacks or warnings.

---

## Technical Specifications

| Specification | Details |
| :--- | :--- |
| **Odoo Compatibility** | Odoo 19.0 Community & Enterprise |
| **Python Compatibility**| Python 3.12+ |
| **Key Dependencies** | `openpyxl >= 3.1.0`, `Pillow >= 10.0.0` |
| **Supported File Formats** | Input: `.xlsx` (OpenXML Workbook); Output: `.xlsx` or `.zip` |
| **Macro Security** | `.xlsm` and workbooks containing `xl/vbaProject.bin` are strictly blocked |
| **Maximum File Size** | 10 MB per template |
| **Calculation Engine** | Excel-native recalculation on load via `fullCalcOnLoad = True` |
| **Controller Route** | `/excel_template_report/download` (HTTP GET/POST, `auth='user'`) |
| **Database Transactions** | Zero database modifications during render operations; pure read-only streaming |

---

## License & Support

- **License**: GNU Lesser General Public License v3.0 (`LGPL-3`).
- **Author**: Dat Nguyen
- **Repository**: [https://github.com/unclecatvn](https://github.com/unclecatvn)
- **Support Contact**: dat030602@gmail.com
