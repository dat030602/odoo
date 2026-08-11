# Excel Template Engine — Technical Developer Guide

> **Module:** `base_excel_report_v2` (Sections 1–13) + Server Action integration (Section 14, Odoo 19)
> **Odoo Version:** Core engine (Sections 1–13) written against 16.0, patterns apply to 14.0/15.0/17.0. Section 14 verified against actual 19.0 source.
> **Status:** Design + reference implementation (Giai đoạn 1 — flat `for`, no nesting)
> **Depends on:** `openpyxl`, `simpleeval`
> **Supersedes:** `base_excel_report` (marker-based `<TABLE_START>` framework)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Module Structure](#2-module-structure)
3. [Installation & Dependencies](#3-installation--dependencies)
4. [Template Syntax Reference](#4-template-syntax-reference)
5. [Core Implementation](#5-core-implementation)
   - 5.1 [`TemplateEngine` class](#51-templateengine-class)
   - 5.2 [Block parsing (`parse_blocks`)](#52-block-parsing-parse_blocks)
   - 5.3 [Block expansion (`expand_for_block`)](#53-block-expansion-expand_for_block)
   - 5.4 [Placeholder resolution (`resolve_placeholders`)](#54-placeholder-resolution-resolve_placeholders)
   - 5.5 [Sum / aggregate filters (`resolve_sum_filters`)](#55-sum--aggregate-filters-resolve_sum_filters)
   - 5.6 [Path resolution (`resolve_path`)](#56-path-resolution-resolve_path)
6. [Base Model — `base.excel.report`](#6-base-model--baseexcelreport)
7. [Hook Method Reference](#7-hook-method-reference)
8. [Creating a Child Module — Step by Step](#8-creating-a-child-module--step-by-step)
9. [Group / Subtotal Reports (Giai đoạn 2 preview)](#9-group--subtotal-reports-giai-đoạn-2-preview)
10. [Testing Strategy](#10-testing-strategy)
11. [Error Reference](#11-error-reference)
12. [Migration Guide from `base_excel_report`](#12-migration-guide-from-baseexcelreport)
13. [Known Limitations (Giai đoạn 1)](#13-known-limitations-giai-đoạn-1)
14. [Server Action Integration (Odoo 19)](#14-server-action-integration-odoo-19)
    - 14.1 [Why Server Action instead of a child module](#141-why-server-action-instead-of-a-child-module)
    - 14.2 [`ir.attachment` extension](#142-irattachment-extension)
    - 14.3 [`ir.actions.server` extension — full code](#143-iractionsserver-extension--full-code)
    - 14.4 [`base.excel.report` — shared generate method](#144-baseexcelreport--shared-generate-method)
    - 14.5 [View XML](#145-view-xml)
    - 14.6 [Security](#146-security)
    - 14.7 [Manifest](#147-manifest)
    - 14.8 [End-to-end usage example](#148-end-to-end-usage-example)
    - 14.9 [Odoo 16 → 19 differences that affected this design](#149-odoo-16--19-differences-that-affected-this-design)
    - 14.10 [Caveats specific to this integration](#1410-caveats-specific-to-this-integration)
15. [Quick Reference Card](#15-quick-reference-card)

---

## 1. Overview

`base_excel_report_v2` replaces hand-written `_write_table_data()` /
`_get_header_footer_data()` hooks with a **single JSON context** produced by
the child module, matched against a `.xlsx` template that declares its own
loops and placeholders inline — similar in spirit to `report_py3o` (Genshi
on ODF) but running natively on `openpyxl`, with no LibreOffice dependency.

**Child module responsibility shrinks to one hook:**

```python
def _get_report_context(self):
    return {"company": {...}, "lines": [...]}
```

Everything else — inserting rows, copying styles, replacing placeholders,
computing `SUBTOTAL` formulas — is handled by `TemplateEngine`.

---

## 2. Module Structure

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

`template_engine.py` is deliberately **framework-agnostic** — it operates on
an `openpyxl.Worksheet` and a plain `dict`/`list` context, with zero Odoo
imports. This lets you unit-test it outside Odoo entirely (see Section 10).

---

## 3. Installation & Dependencies

```bash
pip install openpyxl simpleeval
```

| Package | Purpose |
|---|---|
| `openpyxl` | Read/write `.xlsx`, same as v1 |
| `simpleeval` | Safe expression evaluation for `{% if %}` conditions — **do not use bare `eval()`** on user-uploaded template strings (see Section 4.3 and 11) |

```python
'depends': ['base_excel_report_v2'],
```

```python
# Odoo shell sanity check
import openpyxl, simpleeval
print(openpyxl.__version__, simpleeval.__version__)
```

---

## 4. Template Syntax Reference

### 4.1 Placeholders — `{{ path }}`

```
{{ company.name }}
{{ line.date }}
{{ line.partner.city }}
{{ line.amount | fmt:'#,##0.00' }}
```

- Path resolution tries `dict.get` first, then `getattr` — works transparently
  with plain dicts, Odoo recordsets, or nested objects.
- `| fmt:'...'` sets `cell.number_format` instead of embedding the format in
  the string.
- A resolved value starting with `=` is written as a live Excel formula.

### 4.2 Loop blocks — `{% for x in path %}` … `{% endfor %}`

```
A4:  {% for line in lines %}
A5:  {{ line.name }}   B5: {{ line.date }}   C5: {{ line.amount }}
A6:  {% endfor %}
```

- Marker must be the **only content** of the leftmost non-empty cell in its row.
- The loop body is every row strictly between the two marker rows (1 or more
  rows per item is supported — e.g. a 2-row card layout per record).
- Giai đoạn 1 supports **flat** `for` only. Nesting is Giai đoạn 2 (Section 9).

### 4.3 Conditionals — `{% if expr %}` … `{% endif %}`

```
A9:  {% if line.amount > 1000000 %}
B9:  {{ line.name }} (VIP)
A10: {% endif %}
```

- `expr` is evaluated with `simpleeval.EvalWithCompoundTypes`, context =
  current loop variables only (no arbitrary Python — see Section 11).

### 4.4 Aggregate filters — `sum`, `count`, `avg`, `max`, `min`

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

### 4.5 Image filter — `image`

```
{{ line.photo_base64 | image }}
{{ company.logo_url | image:width=120,height=60 }}
```

Not implemented in Giai đoạn 1 reference code below — stubbed with a clear
`NotImplementedError` pointing to Section 13.

---

## 5. Core Implementation

### 5.1 `TemplateEngine` class

```python
# models/template_engine.py
# -*- coding: utf-8 -*-
"""
Pure-Python template engine for openpyxl worksheets.
No Odoo imports here — keep this file unit-testable standalone.
"""
import re
from dataclasses import dataclass, field
from typing import Any

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from simpleeval import EvalWithCompoundTypes

FOR_RE     = re.compile(r'^\{%\s*for\s+(\w+)\s+in\s+([\w.]+)\s*%\}$')
ENDFOR_RE  = re.compile(r'^\{%\s*endfor\s*%\}$')
IF_RE      = re.compile(r'^\{%\s*if\s+(.+?)\s*%\}$')
ENDIF_RE   = re.compile(r'^\{%\s*endif\s*%\}$')
PLACEHOLDER_RE = re.compile(r'\{\{\s*(.+?)\s*\}\}')
AGG_FUNCS  = {'sum': 9, 'avg': 1, 'count': 2, 'max': 4, 'min': 5}


class TemplateError(Exception):
    """Raised for any template syntax/resolution error. Caught by the
    Odoo layer and re-raised as UserError with a friendly message."""


@dataclass
class Block:
    kind: str            # 'for' | 'if'
    start_row: int        # row of the {% ... %} marker
    end_row: int           # row of the {% end... %} marker
    var_name: str = ''    # only for 'for'
    iter_path: str = ''   # only for 'for'
    condition: str = ''   # only for 'if'
    depth: int = 0
    children: list = field(default_factory=list)


class TemplateEngine:
    """Renders a template Worksheet in-place against a context dict."""

    def __init__(self, sheet: Worksheet, marker_column: int = 1):
        self.sheet = sheet
        self.marker_column = marker_column
        # populated during expand(); consumed by resolve_sum_filters()
        self.expanded_ranges: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def render(self, context: dict):
        blocks = self.parse_blocks()
        # Deepest blocks first: expanding an outer block shifts row numbers
        # for everything below it, so inner blocks must be resolved first
        # relative to a stable coordinate system. In Giai đoạn 1 (flat only)
        # this sort is trivial (max depth 1) but kept for forward-compat
        # with Giai đoạn 2 nesting.
        blocks.sort(key=lambda b: -b.depth)

        for block in blocks:
            if block.kind == 'for':
                self.expand_for_block(block, context)
            elif block.kind == 'if':
                self.expand_if_block(block, context)

        self.resolve_placeholders(self.sheet, context)
        self.resolve_sum_filters(context)

    # ------------------------------------------------------------------ #
    # 5.2  Block parsing
    # ------------------------------------------------------------------ #
    def parse_blocks(self) -> list[Block]:
        """Scan the marker column top-to-bottom, matching {% %} pairs with
        a stack so nested blocks (Giai đoạn 2) parse correctly today even
        though expand() only handles depth-1 for now."""
        stack: list[Block] = []
        finished: list[Block] = []

        max_row = self.sheet.max_row
        for row in range(1, max_row + 1):
            cell = self.sheet.cell(row=row, column=self.marker_column)
            value = (cell.value or '').strip() if isinstance(cell.value, str) else ''
            if not value:
                continue

            m_for = FOR_RE.match(value)
            m_if = IF_RE.match(value)
            m_endfor = ENDFOR_RE.match(value)
            m_endif = ENDIF_RE.match(value)

            if m_for:
                stack.append(Block(
                    kind='for', start_row=row, end_row=-1,
                    var_name=m_for.group(1), iter_path=m_for.group(2),
                    depth=len(stack),
                ))
            elif m_if:
                stack.append(Block(
                    kind='if', start_row=row, end_row=-1,
                    condition=m_if.group(1), depth=len(stack),
                ))
            elif m_endfor or m_endif:
                if not stack:
                    raise TemplateError(
                        f"Unmatched '{value}' at row {row}: no open block."
                    )
                block = stack.pop()
                expected = 'for' if m_endfor else 'if'
                if block.kind != expected:
                    raise TemplateError(
                        f"Mismatched block at row {row}: expected "
                        f"'{{% end{block.kind} %}}', got '{value}'."
                    )
                block.end_row = row
                if stack:
                    stack[-1].children.append(block)
                finished.append(block)

        if stack:
            unclosed = stack[-1]
            raise TemplateError(
                f"Unclosed '{{% {unclosed.kind} %}}' opened at row "
                f"{unclosed.start_row}."
            )
        return finished

    # ------------------------------------------------------------------ #
    # 5.3  Block expansion
    # ------------------------------------------------------------------ #
    def expand_for_block(self, block: Block, context: dict):
        items = self.resolve_path(block.iter_path, context)
        if items is None:
            items = []
        items = list(items)

        body_start = block.start_row + 1
        body_end   = block.end_row - 1
        body_height = body_end - body_start + 1

        if body_height < 1:
            raise TemplateError(
                f"Empty loop body for '{{% for {block.var_name} in "
                f"{block.iter_path} %}}' at row {block.start_row}."
            )

        n = len(items)
        if n == 0:
            # No data: delete the entire block (markers + body)
            self.sheet.delete_rows(block.start_row,
                                    amount=block.end_row - block.start_row + 1)
            self.expanded_ranges[id(block)] = (block.start_row, block.start_row - 1)
            return

        # Insert (n - 1) additional copies of the body BELOW the existing one
        extra_rows = body_height * (n - 1)
        if extra_rows:
            self.sheet.insert_rows(body_end + 1, amount=extra_rows)

        # Copy styles + raw template text from the first body copy into
        # every subsequent copy (openpyxl.insert_rows() does not clone
        # styles by itself)
        first_copy_rows = list(range(body_start, body_end + 1))
        for copy_idx in range(1, n):
            offset = copy_idx * body_height
            for src_row in first_copy_rows:
                dst_row = src_row + offset
                self._copy_row(src_row, dst_row)

        # Now resolve {{ }} placeholders in each copy against its own item
        for copy_idx, item in enumerate(items):
            offset = copy_idx * body_height
            item_context = dict(context)
            item_context[block.var_name] = item
            for src_row in first_copy_rows:
                dst_row = src_row + offset
                self.resolve_placeholders(
                    self.sheet, item_context,
                    row_range=(dst_row, dst_row),
                )

        actual_end = body_start + n * body_height - 1
        self.expanded_ranges[block.var_name] = (body_start, actual_end)

        # Delete the two marker rows themselves (now at their shifted
        # positions: the {% for %} row is untouched at block.start_row,
        # the {% endfor %} row shifted down by extra_rows)
        self.sheet.delete_rows(block.start_row, amount=1)
        # After deleting the opening marker, everything shifts up by 1
        self.sheet.delete_rows(block.end_row + extra_rows - 1, amount=1)

    def expand_if_block(self, block: Block, context: dict):
        try:
            evaluator = EvalWithCompoundTypes(names=context)
            result = bool(evaluator.eval(block.condition))
        except Exception as exc:
            raise TemplateError(
                f"Failed to evaluate condition '{block.condition}' at row "
                f"{block.start_row}: {exc}"
            ) from exc

        if result:
            # keep body, drop the two marker rows
            self.sheet.delete_rows(block.end_row, amount=1)
            self.sheet.delete_rows(block.start_row, amount=1)
        else:
            self.sheet.delete_rows(block.start_row,
                                    amount=block.end_row - block.start_row + 1)

    def _copy_row(self, src_row: int, dst_row: int):
        """Clone values + styles from src_row to dst_row across all
        populated columns. Mirrors v1's _copy_row_styles() but also
        copies the raw {{ }} template text, since dst_row starts blank
        after insert_rows()."""
        max_col = self.sheet.max_column
        for col in range(1, max_col + 1):
            src = self.sheet.cell(row=src_row, column=col)
            dst = self.sheet.cell(row=dst_row, column=col)
            dst.value = src.value
            if src.has_style:
                dst.font = src.font.copy()
                dst.border = src.border.copy()
                dst.fill = src.fill.copy()
                dst.alignment = src.alignment.copy()
                dst.number_format = src.number_format
        # row height
        if src_row in self.sheet.row_dimensions:
            self.sheet.row_dimensions[dst_row].height = \
                self.sheet.row_dimensions[src_row].height

    # ------------------------------------------------------------------ #
    # 5.4  Placeholder resolution (non-loop {{ }} and per-row during expand)
    # ------------------------------------------------------------------ #
    def resolve_placeholders(self, sheet: Worksheet, context: dict,
                              row_range: tuple[int, int] | None = None):
        rows = range(row_range[0], row_range[1] + 1) if row_range \
            else range(1, sheet.max_row + 1)

        for row in rows:
            for col in range(1, sheet.max_column + 1):
                cell = sheet.cell(row=row, column=col)
                if not isinstance(cell.value, str) or '{{' not in cell.value:
                    continue
                # Skip filter-only aggregate expressions; those are handled
                # by resolve_sum_filters() so the SUBTOTAL formula isn't
                # clobbered by a plain string substitution here.
                if self._is_aggregate_expr(cell.value):
                    continue

                new_value, is_formula, number_format = \
                    self._render_cell_text(cell.value, context)

                cell.value = new_value
                if number_format:
                    cell.number_format = number_format

    def _is_aggregate_expr(self, text: str) -> bool:
        m = PLACEHOLDER_RE.search(text)
        if not m:
            return False
        expr = m.group(1)
        if '|' not in expr:
            return False
        filt = expr.split('|', 1)[1].strip()
        return filt.split(':', 1)[0].strip() in AGG_FUNCS

    def _render_cell_text(self, text: str, context: dict):
        number_format = None

        def _sub(m: re.Match) -> str:
            nonlocal number_format
            expr = m.group(1)
            path, *filters = [p.strip() for p in expr.split('|')]
            value = self.resolve_path(path, context)
            for filt in filters:
                name, _, arg = filt.partition(':')
                name = name.strip()
                arg = arg.strip().strip("'\"")
                if name == 'fmt':
                    number_format = arg
                    value = value  # formatting applied via cell.number_format
                elif name == 'image':
                    raise TemplateError(
                        "Image filter used outside a supported context. "
                        "See Section 13 (Known Limitations, Giai đoạn 1)."
                    )
            return '' if value is None else str(value)

        rendered = PLACEHOLDER_RE.sub(_sub, text)
        is_formula = rendered.startswith('=')
        return rendered, is_formula, number_format

    # ------------------------------------------------------------------ #
    # 5.5  Sum / aggregate filters
    # ------------------------------------------------------------------ #
    def resolve_sum_filters(self, context: dict):
        for row in range(1, self.sheet.max_row + 1):
            for col in range(1, self.sheet.max_column + 1):
                cell = self.sheet.cell(row=row, column=col)
                if not isinstance(cell.value, str) or '{{' not in cell.value:
                    continue
                m = PLACEHOLDER_RE.search(cell.value)
                if not m or '|' not in m.group(1):
                    continue
                path, _, filt = m.group(1).partition('|')
                path = path.strip()
                name, _, arg = filt.strip().partition(':')
                name = name.strip()
                if name not in AGG_FUNCS:
                    continue

                if path not in self.expanded_ranges:
                    raise TemplateError(
                        f"Aggregate filter '{name}' at row {row} references "
                        f"'{path}', which is not a known expanded loop "
                        f"variable name. Check that the for-block uses "
                        f"'{{% for x in {path} %}}' with a matching name."
                    )
                start, end = self.expanded_ranges[path]
                col_letter = get_column_letter(col)
                code = AGG_FUNCS[name]
                if end < start:
                    formula = 0  # loop rendered zero rows — nothing to sum
                else:
                    formula = f'=SUBTOTAL({code},{col_letter}{start}:{col_letter}{end})'
                cell.value = formula

    # ------------------------------------------------------------------ #
    # 5.6  Path resolution
    # ------------------------------------------------------------------ #
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

### Design notes on the code above

- **`expand_for_block` order of operations matters.** Styles/text are cloned
  into every copy *before* per-item placeholder resolution, otherwise later
  copies would resolve against already-substituted (no longer `{{ }}`)
  text from the first copy.
- **Marker rows are deleted last**, after `expanded_ranges` has been
  recorded, so the recorded `(start_row, end_row)` reflects the final data
  position that `resolve_sum_filters()` needs — matching the v1 requirement
  that `_get_header_footer_data(start_row, end_row, ...)` receive final
  positions (Section 7 of the v1 doc).
- **`_is_aggregate_expr` guard** prevents `resolve_placeholders` from
  stringifying a `{{ lines | sum:'amount' }}` cell into `"[]"` or similar
  before `resolve_sum_filters` gets a chance to turn it into a formula.

---

## 6. Base Model — `base.excel.report`

```python
# models/base_excel_report.py
# -*- coding: utf-8 -*-
import base64
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import openpyxl

from .template_engine import TemplateEngine, TemplateError

FAST_MODE_THRESHOLD = 1000  # kept for parity with v1; see Section 13


class BaseExcelReport(models.TransientModel):
    _name = 'base.excel.report'
    _description = 'Base Excel Report (Template Engine v2)'

    state = fields.Selection(
        [('choose', 'Choose'), ('download', 'Download')],
        default='choose',
    )
    excel_file = fields.Binary('Excel File', readonly=True)
    excel_filename = fields.Char('Filename', readonly=True)

    # ------------------------------------------------------------------ #
    # Hook — required
    # ------------------------------------------------------------------ #
    def _get_template_name(self):
        raise NotImplementedError(
            "_get_template_name() must be implemented by the child module."
        )

    def _get_report_context(self):
        raise NotImplementedError(
            "_get_report_context() must be implemented by the child module."
        )

    # ------------------------------------------------------------------ #
    # Hook — optional
    # ------------------------------------------------------------------ #
    def _get_output_filename(self):
        name = self._get_template_name()
        base = name[:-5] if name.endswith('.xlsx') else name
        if base.startswith('template_'):
            base = base[len('template_'):]
        return f'{base}_output.xlsx'

    # ------------------------------------------------------------------ #
    # Pipeline — do not override
    # ------------------------------------------------------------------ #
    def action_generate_excel(self):
        self.ensure_one()
        workbook = self._load_template()
        sheet = workbook.active

        context = self._get_report_context()
        if not isinstance(context, dict):
            raise UserError(_(
                "_get_report_context() must return a dict, got %s."
            ) % type(context).__name__)

        engine = TemplateEngine(sheet)
        try:
            engine.render(context)
        except TemplateError as exc:
            raise UserError(_(
                "Error rendering Excel template '%(tpl)s': %(err)s"
            ) % {'tpl': self._get_template_name(), 'err': str(exc)})

        return self._export_file(workbook)

    def _load_template(self):
        template_name = self._get_template_name()
        attachment = self.env['ir.attachment'].search(
            [('name', '=', template_name)], limit=1
        )
        if not attachment:
            raise UserError(_(
                "Template file '%s' was not found in Attachments."
            ) % template_name)
        try:
            data = base64.b64decode(attachment.datas)
            return openpyxl.load_workbook(BytesIO(data))
        except Exception as exc:
            raise UserError(_(
                "Failed to read the Excel template '%(name)s': %(err)s"
            ) % {'name': template_name, 'err': str(exc)})

    def _export_file(self, workbook):
        stream = BytesIO()
        workbook.save(stream)
        self.write({
            'excel_file': base64.b64encode(stream.getvalue()),
            'excel_filename': self._get_output_filename(),
            'state': 'download',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
```

Compared to v1's `action_generate_excel()`, the pipeline collapses from
10 steps to essentially **3**: load template → build context → render.
Row insertion, style copying, placeholder substitution, and `SUBTOTAL`
formula generation all live inside `TemplateEngine.render()`.

---

## 7. Hook Method Reference

| Method | Required | Signature | Returns |
|---|---|---|---|
| `_get_template_name` | ✅ | `(self)` | `str` — attachment name, unchanged from v1 |
| `_get_report_context` | ✅ | `(self)` | `dict` — arbitrarily nested dicts/lists/recordsets |
| `_get_output_filename` | ⬜ | `(self)` | `str`, defaults to `{template_base}_output.xlsx` |

Note what's **gone** versus v1: `_write_table_data`, `_get_header_footer_data`,
and the `sheet`/`start_row`/`start_col` parameters child code used to
manipulate directly. Child modules no longer import `openpyxl` at all.

---

## 8. Creating a Child Module — Step by Step

### 8.1 Template file (`template_sale_report.xlsx`)

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

### 8.2 Python model

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

That's the entire child module's business logic — no `openpyxl` import,
no row/column math, no manual `SUBTOTAL` string building.

### 8.3 Manifest

```python
{
    'name': 'Sale Excel Report',
    'version': '16.0.1.0.0',
    'depends': ['base_excel_report_v2', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_sale_excel_report_views.xml',
    ],
}
```

---

## 9. Group / Subtotal Reports (Giai đoạn 2 preview)

Not implemented in the reference code above (Giai đoạn 1 supports flat
loops only). The intended shape, once nested `for` is added to
`expand_for_block`:

```
{% for g in groups %}
  {% for l in g.lines %}
  {{ l.name }}   {{ l.amount }}
  {% endfor %}
  Subtotal {{ g.name }}   {{ g.lines | sum:'amount' }}
{% endfor %}
```

```python
def _get_report_context(self):
    orders = self.env['sale.order'].search([], order='partner_id, date_order')
    groups = {}
    for o in orders:
        groups.setdefault(o.partner_id, []).append(o)
    return {
        'groups': [
            {
                'name': partner.name,
                'lines': [{'name': o.name, 'amount': o.amount_total} for o in ords],
            }
            for partner, ords in groups.items()
        ],
    }
```

Implementation requires: (a) `expand_for_block` to recurse into
`block.children` before resolving the parent's own iteration, and
(b) `expanded_ranges` to be keyed per-iteration rather than globally per
variable name, since `g.lines` produces a *different* row range for each
group. This is flagged explicitly because the reference implementation in
Section 5 uses a flat dict for `expanded_ranges` that would silently
overwrite entries across groups — do not reuse it as-is for nested loops.

---

## 10. Testing Strategy

`template_engine.py` has no Odoo imports, so test it with plain `pytest`,
independent of an Odoo database:

```python
# tests/test_template_engine.py
import openpyxl
from base_excel_report_v2.models.template_engine import TemplateEngine

def make_sheet(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r, row_values in enumerate(rows, start=1):
        for c, value in enumerate(row_values, start=1):
            ws.cell(row=r, column=c, value=value)
    return ws

def test_flat_for_expands_correctly():
    ws = make_sheet([
        ['{% for line in lines %}'],
        ['{{ line.name }}', '{{ line.amount }}'],
        ['{% endfor %}'],
    ])
    engine = TemplateEngine(ws)
    engine.render({'lines': [{'name': 'A', 'amount': 10},
                              {'name': 'B', 'amount': 20}]})
    assert ws.cell(row=1, column=1).value == 'A'
    assert ws.cell(row=1, column=2).value == 10
    assert ws.cell(row=2, column=1).value == 'B'
    assert ws.cell(row=2, column=2).value == 20

def test_sum_filter_produces_subtotal_formula():
    ws = make_sheet([
        ['{% for line in lines %}'],
        ['{{ line.amount }}'],
        ['{% endfor %}'],
        ['{{ lines | sum:"amount" }}'],
    ])
    engine = TemplateEngine(ws)
    engine.render({'lines': [{'amount': 10}, {'amount': 20}, {'amount': 30}]})
    # 3 items -> occupy rows 1-3, sum formula lands on row 4
    assert ws.cell(row=4, column=1).value == '=SUBTOTAL(9,A1:A3)'

def test_empty_list_deletes_block_and_sum_is_zero():
    ws = make_sheet([
        ['{% for line in lines %}'],
        ['{{ line.amount }}'],
        ['{% endfor %}'],
        ['{{ lines | sum:"amount" }}'],
    ])
    engine = TemplateEngine(ws)
    engine.render({'lines': []})
    assert ws.cell(row=1, column=1).value == 0

def test_unclosed_block_raises():
    ws = make_sheet([['{% for line in lines %}'], ['{{ line.name }}']])
    engine = TemplateEngine(ws)
    import pytest
    from base_excel_report_v2.models.template_engine import TemplateError
    with pytest.raises(TemplateError, match="Unclosed"):
        engine.render({'lines': []})
```

**Merged-cell and formula-shift regression tests are mandatory before this
module leaves Giai đoạn 1** — the risks in Section 13 have no automated
coverage in the reference implementation above and must be added
per-fixture (a template file with a merged cell inside a loop body, a
template with a cross-sheet formula reference) before any child module
depends on those layouts.

---

## 11. Error Reference

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

---

## 12. Migration Guide from `base_excel_report`

| v1 concept | v2 equivalent |
|---|---|
| `<TABLE_START>` marker | `{% for line in lines %}` / `{% endfor %}` pair |
| `_get_report_data()` returning Recordset/list | Build the equivalent list inside `_get_report_context()['lines']` |
| `_write_table_data(sheet, data, start_row, start_col)` | Delete — replaced by `{{ line.field }}` in the template |
| `_get_header_footer_data()` returning `{'{{KEY}}': value}` | Delete — put values straight into the context dict, reference as `{{ key }}` in the template |
| `Grand Total` placeholder + manual `SUBTOTAL` formula string | `{{ lines \| sum:'field' }}` |
| Fast Mode (`FAST_MODE_THRESHOLD`) skipping `_copy_row_styles` / `_autofit_columns` | Not yet ported — see Section 13 |
| Column-level number formatting workaround for Fast Mode | Still valid; `\| fmt:'...'` is a per-cell alternative for Normal-Mode-only usage today |

**Migration is not automatic.** Existing `.xlsx` templates using
`<TABLE_START>` will not work with `base_excel_report_v2` — templates must
be rewritten with `{% for %}` markers. Recommend migrating one report at a
time rather than a bulk cutover, given the merged-cell/formula risks in
Section 13 are not yet covered by regression tests.

---

## 13. Known Limitations (Giai đoạn 1)

These are carried over from the design spec's risk analysis and remain
**unresolved in the reference code above** — do not treat this module as
production-ready until they are addressed:

1. **Merged cells inside a loop body are not handled.** `insert_rows()` /
   `_copy_row()` above do not detect or re-create `MergedCellRange`s. A
   template with a merged cell inside `{% for %}...{% endfor %}` will
   produce corrupted or duplicated merge ranges.
2. **Static images do not shift.** A logo placed below a `for` block will
   not move down when the block expands. Keep static images above the
   first loop, or defer to a "footer-above-data" layout (same
   recommendation as v1 Section 8.2).
3. **`image` filter is unimplemented** — raises `TemplateError` if used.
   Planned for Giai đoạn 3.
4. **Nested `for` is parsed but not expanded** — `parse_blocks()` builds
   the correct `children` tree, but `expand_for_block()` only processes
   top-level blocks. Using nested loops today will silently leave inner
   `{% for %}` markers unexpanded as literal text. Guard this explicitly
   in `render()` until Giai đoạn 2 lands:

   ```python
   for block in blocks:
       if block.children:
           raise TemplateError(
               f"Nested loops are not yet supported (Giai đoạn 2). "
               f"Found nested block inside row {block.start_row}."
           )
   ```

   *(Add this guard to `render()` before shipping Giai đoạn 1 — it is
   omitted from Section 5.1 above for readability but is required.)*
5. **Fast Mode is not ported.** Every render does full per-cell style
   copying regardless of row count. Benchmark before assuming the v1
   1 000-row default threshold still applies — the per-row work here is
   heavier (regex + path resolution) than v1's direct attribute assignment.
6. **Cross-sheet and 3D formula references** are not verified safe across
   `insert_rows()`/`delete_rows()`. Test explicitly if a template's
   `for` block sits above/beside such formulas.

---

## 14. Server Action Integration (Odoo 19)

### 14.1 Why Server Action instead of a child module

Sections 6–8 describe a child `TransientModel` per report (30–50 lines,
its own `__manifest__.py`, its own view XML). For reports that don't need
a custom filter UI beyond a domain/selection already available on the
source model's list view, that scaffolding is unnecessary — the only
real per-report logic is "build a dict from these records."

`ir.actions.server` already provides exactly this entry point: a record
users configure through the UI, bound to a model, with a `code` field for
short Python snippets and a **Run** button (via "Create Contextual Action",
appearing in the target model's Action menu). This section wires
`TemplateEngine` / `base.excel.report` (Sections 5–6, unchanged) directly
into that mechanism, so a new report becomes **one `ir.actions.server`
record**, configured entirely from Settings → Technical, with zero new
Python files.

**What stays exactly as-is:** `template_engine.py` (Section 5) and the
core of `base_excel_report.py` (Section 6) — this integration only adds a
dispatch branch, it does not change how templates are parsed or rendered.

**What this trades away:** per-report `ir.model.access.csv` entries, a
dedicated wizard form for custom filters (date ranges, checkboxes), and
compile-time type safety on the context-building code (it's a `Text`
field evaluated with `safe_eval`, not a reviewed Python file — see 15.10).
Use the child-module pattern from Section 8 when a report needs its own
filter form or must be locked down per-report via ACLs; use this pattern
for internal/admin-facing reports where the source model's own list-view
domain is filter enough.

### 14.2 `ir.attachment` extension

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

### 14.3 `ir.actions.server` extension — full code

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
    excel_template_attachment = fields.Many2one(
        'ir.attachment',
        string='Excel Template',
        domain=[('is_excel_template', '=', True)],
        help="Template file uploaded to Attachments with "
             "'Is Excel Template' checked.",
    )

    # ------------------------------------------------------------------ #
    # Odoo 19 uses a non-blocking warning banner (_get_warning_messages /
    # _compute_warning) for action misconfiguration instead of a hard
    # ValidationError constraint. Follow that convention here rather than
    # @api.constrains, so an incomplete action can still be saved as a
    # draft and only fails when actually Run.
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Dispatch target. Odoo's _get_runner() looks up
    # `_run_action_{state}_multi` first (falls back to the non-multi
    # variant if absent). The `_multi` suffix means this method receives
    # ALL selected records in `eval_context['records']` in a single call
    # instead of being invoked once per record — required here so that a
    # multi-select in a list view produces ONE Excel file, not one per row.
    # ------------------------------------------------------------------ #
    def _run_action_excel_template_multi(self, eval_context=None):
        self.ensure_one()
        if not self.excel_template_attachment:
            raise UserError(_(
                "No Excel template selected for this server action."
            ))

        # `code` carries the same protection as the built-in 'Execute
        # Code' state: field-level `groups='base.group_system'` plus
        # Odoo 19's automatic ir.actions.server.history versioning on
        # every write() to this field (see Section 15.9).
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
            self.excel_template_attachment, report_context
        )
```

### 14.4 `base.excel.report` — shared generate method

Add this method alongside the existing `action_generate_excel()` pipeline
from Section 6. It is the method both the hook-based wizard flow *and*
the Server Action flow above call into — the only difference between the
two entry points is where `(attachment, context)` comes from.

```python
# models/base_excel_report.py  (addition to the class from Section 6)
import base64
from io import BytesIO

import openpyxl
from odoo import _
from odoo.exceptions import UserError

from .template_engine import TemplateEngine, TemplateError


class BaseExcelReport(models.TransientModel):
    _name = 'base.excel.report'
    # ... state, excel_file, excel_filename fields as in Section 6 ...

    def _generate_from_attachment(self, attachment, context):
        """Render `attachment` (an ir.attachment holding a .xlsx template)
        against `context` (a plain dict) and store the result on this
        wizard record. Called by action_generate_excel() (via the
        _get_template_name/_get_report_context hooks) and directly by
        ir.actions.server._run_action_excel_template_multi()."""
        self.ensure_one()
        try:
            data = base64.b64decode(attachment.datas)
            workbook = openpyxl.load_workbook(BytesIO(data))
        except Exception as exc:
            raise UserError(_(
                "Failed to read the Excel template '%(name)s': %(err)s"
            ) % {'name': attachment.name, 'err': str(exc)})

        sheet = workbook.active
        engine = TemplateEngine(sheet)
        try:
            engine.render(context)
        except TemplateError as exc:
            raise UserError(_(
                "Error rendering Excel template '%(tpl)s': %(err)s"
            ) % {'tpl': attachment.name, 'err': str(exc)})

        return self._export_file(workbook)
```

### 14.5 View XML

Add the template field to the Server Action form, visible only when
`state == 'excel_template'`:

```xml
<!-- views/ir_actions_server_views.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_server_action_form_excel" model="ir.ui.view">
        <field name="name">ir.actions.server.form.excel.template</field>
        <field name="model">ir.actions.server</field>
        <field name="inherit_id" ref="base.view_server_action_form"/>
        <field name="arch" type="xml">
            <field name="code" position="after">
                <field name="excel_template_attachment"
                       invisible="state != 'excel_template'"
                       required="state == 'excel_template'"/>
            </field>
        </field>
    </record>
</odoo>
```

> Odoo 19 form views use the `invisible`/`required` string-expression
> attribute syntax shown above (not the old `attrs="{...}"` dict syntax
> from ≤16, which is deprecated).

### 14.6 Security

```csv
# security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_ir_attachment_is_excel_template,ir.attachment.is_excel_template,base.model_ir_attachment,base.group_system,1,1,1,0
```

No new access rule is needed for `ir.actions.server` itself — it already
ships Odoo's standard ACLs, and the `code` field (reused here for
`excel_context`) is already restricted to `base.group_system` at the
field level, which is what actually gates who can configure this.

### 14.7 Manifest

```python
# __manifest__.py
{
    'name': 'Excel Template Engine — Server Action Integration',
    'version': '19.0.1.0.0',
    'depends': ['base_excel_report_v2', 'base'],
    'external_dependencies': {'python': ['openpyxl', 'simpleeval']},
    'data': [
        'security/ir.model.access.csv',
        'views/ir_actions_server_views.xml',
    ],
}
```

### 14.8 End-to-end usage example

1. Upload `template_sale_report.xlsx` (syntax per Section 4) to
   Attachments, check **Is Excel Template**.
2. Settings → Technical → Actions → Server Actions → New.
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
3. Click **Create Contextual Action** so the action appears in the
   Action menu on `sale.order`'s list view.
4. From the list view: select rows → Action → *(action name)* → Run.
   All selected rows are passed as `records` in one call
   (`_run_action_excel_template_multi`), producing a single file.

### 14.9 Odoo 16 → 19 differences that affected this design

The original sketch of this integration (see prior discussion) was
written against Odoo 16 source. Verified against the actual 19.0
`ir_actions.py` before finalizing the code above:

| | 16.0 | 19.0 | Effect on this integration |
|---|---|---|---|
| Groups field name | `groups_id` | `group_ids` | Not touched by our code — we don't declare a new groups field, so no change needed |
| `_get_runner()` | Falls back to deprecated public `run_action_%s[_multi]` names | Fallback removed; only `_run_action_{state}_multi` / `_run_action_{state}` | None — we always used the private-prefixed name |
| `code` field default | Pre-filled `DEFAULT_PYTHON_CODE` sample | No default, empty | None — cosmetic only |
| Config-error UX | Hard `@api.constrains` → blocks save | `_get_warning_messages()` / `_compute_warning()` → non-blocking banner | We used the 19-native warning pattern (15.3) instead of `@api.constrains`, to match how core Odoo now reports server-action misconfiguration |
| Code change tracking | None | `ir.actions.server.history` auto-records every `write()` to `code` | Free bonus: the Python snippet building `excel_context` for each report now has built-in version history and diff view in the UI, no extra work required |
| `ir.actions.act_url` | `target`: `new`, `self` | Adds `target: 'download'` | Considered as an alternative to the wizard-download flow; not adopted — would require writing the generated file to a new `ir.attachment` and exposing it via a controller route, which is more moving parts than the existing Binary-field-on-wizard approach for no functional gain here |

### 14.10 Caveats specific to this integration

1. **`code` is still `safe_eval`, not a real sandbox.** Reusing this field
   means the same trust boundary as core Odoo's "Execute Code" action:
   restricted to `base.group_system` today, and that must not be loosened
   just because the use case here (building a dict) looks harmless —
   `safe_eval` still permits arbitrary attribute access on `env`/`model`.
2. **`_multi` is mandatory.** Implementing `_run_action_excel_template`
   (without the suffix) instead would make Odoo's `run()` loop call it
   once per `active_id`, generating N separate files for N selected
   records instead of one combined file. Confirmed against 19.0's `run()`
   dispatch logic, unchanged from 16.0 in this respect.
3. **No per-report ACLs.** Every user in `base.group_system` who can edit
   this server action can point it at *any* attachment flagged
   `is_excel_template` and write arbitrary `excel_context`-building code.
   If different reports need different edit permissions, use the
   child-module wizard pattern (Section 8) for those specific reports
   instead, and reserve this integration for reports where a shared
   technical/admin audience is acceptable.
4. **`records` is only populated when the action is bound correctly.**
   `_get_eval_context()` sets `records` from `active_ids` only when
   `active_model` matches this action's `model_id` — this is standard
   Odoo behavior (confirmed in both 16.0 and 19.0 source), but it means
   the action must actually be triggered from the model it's bound to
   (via the contextual menu), not run standalone from the Server Actions
   list, or `records` will be empty and `excel_context` will build an
   empty report.

---

## 15. Quick Reference Card

### Template syntax

```
{{ path.to.value }}                    value substitution
{{ value | fmt:'#,##0.00' }}           number/date format
{% for x in path %} ... {% endfor %}   loop block (flat only, Giai đoạn 1)
{% if expr %} ... {% endif %}          conditional block
{{ list_name | sum:'field' }}          =SUBTOTAL(9,...) over the expanded range
{{ list_name | count:'field' }}        =SUBTOTAL(2,...)
{{ list_name | avg:'field' }}          =SUBTOTAL(1,...)
```

### Child module contract

```python
class MyExcelReport(models.TransientModel):
    _name = 'my.excel.report'
    _inherit = 'base.excel.report'

    def _get_template_name(self):
        return 'template_my_report.xlsx'

    def _get_report_context(self):
        return {'lines': [...], 'company': {...}}
```

### Pre-flight checklist for a new template

```
□  Every {% for %} has a matching {% endfor %} (marker cell = leftmost column, exact syntax)
□  No nested {% for %} yet (Giai đoạn 1 limitation — see Section 13.4)
□  {{ list_name | sum:'field' }} uses the SAME name as the for-loop's iterable path
□  No merged cells inside any loop body
□  No static images below a loop block
□  Saved as .xlsx, uploaded to ir.attachment with Name == _get_template_name()
```

---

*Companion document: `excel_template_engine_spec.md` (syntax rationale,
comparison with `report_py3o`, phased rollout plan). This guide is the
implementation-level reference for developers building on top of it.*