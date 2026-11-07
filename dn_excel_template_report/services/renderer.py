# -*- coding: utf-8 -*-
"""Master renderer service coordinating template scanning, expansion, population, and rendering."""

import io
import logging
import re
from typing import Any, Dict, List, Optional

import openpyxl

from .evaluator import build_eval_context, evaluate_expression
from .images import insert_image_into_cell
from .layout import ensure_cell_wrap_text, expand_loop_row, fill_loop_rows
from .parser import scan_sheet
from .resolver import is_html, resolve_path, to_cell_value

_logger = logging.getLogger(__name__)


def render_template(
    template_bytes: bytes,
    record: Any,
    records: Any = None,
    template: Any = None,
    empty_policy: Optional[str] = None,
    strict: bool = False,
) -> bytes:
    """
    Renders an Excel template workbook with data from an Odoo record context.

    Pipeline phases:
      1. Load workbook from bytes (preserving formulas and formatting).
      2. Construct rich evaluation context (record, company, env, helpers).
      3. For each worksheet:
         a. Discover placeholders and loop rows.
         b. Expand and populate loop rows bottom-up (descending row order).
         c. Embed proportionally scaled images.
         d. Rescan and evaluate remaining scalar placeholders.
      4. Flag workbook for full calculation on load (fullCalcOnLoad = True).
      5. Return rendered workbook as raw .xlsx bytes.

    Args:
        template_bytes: Raw bytes of the uploaded .xlsx template file
        record: Primary Odoo record or dictionary providing data context
        records: Recordset for batch operations
        template: Optional excel.report.template model record
        empty_policy: 'keep_blank' | 'remove' (falls back to template.empty_table_policy)
        strict: If True, raise exception on evaluation errors; if False, graceful fallback

    Returns:
        Rendered .xlsx file as raw bytes (PKZip format)
    """
    if not template_bytes:
        raise ValueError("template_bytes must not be empty")

    policy = empty_policy
    if not policy and template and hasattr(template, "empty_table_policy"):
        policy = template.empty_table_policy
    if not policy:
        policy = "keep_blank"

    # 1. Load workbook
    wb = openpyxl.load_workbook(io.BytesIO(template_bytes), data_only=False)

    # 2. Build execution context
    ctx = build_eval_context(record, records=records, template=template)

    # 3. Process each worksheet
    for ws in wb.worksheets:
        scan = scan_sheet(ws)

        # 3a. Process loop rows bottom-up (descending row order)
        sorted_loop_rows = sorted(scan.loop_rows.values(), key=lambda lr: lr.row, reverse=True)
        for lr in sorted_loop_rows:
            ds_name = lr.datasource
            row_data_list: List[Dict[str, Any]] = []

            # 1. Check if Python script provided this table
            py_tables = ctx.get("_python_tables") or {}
            if ds_name in py_tables:
                raw_lines = py_tables[ds_name]
                for idx, line_item in enumerate(raw_lines, start=1):
                    line_ctx = dict(ctx)
                    line_ctx["line"] = line_item
                    line_ctx["idx"] = idx

                    row_dict: Dict[str, Any] = {}
                    for key in lr.columns.values():
                        if isinstance(line_item, dict):
                            row_dict[key] = line_item.get(key)
                        else:
                            val = resolve_path(line_item, key)
                            if val is None and hasattr(line_item, key):
                                val = getattr(line_item, key)
                            row_dict[key] = val
                    row_data_list.append(row_dict)
            else:
                # 2. Check if template defines this datasource (Visual Builder mode)
                ds_def = None
                if template and hasattr(template, "datasource_ids"):
                    ds_matches = template.datasource_ids.filtered(lambda d: d.name == ds_name)
                    if ds_matches:
                        ds_def = ds_matches[0]

                raw_lines = None
                if ds_def and ds_def.rows_expr:
                    raw_lines = evaluate_expression(ds_def.rows_expr, ctx, strict=strict)
                else:
                    raw_lines = evaluate_expression(ds_name, ctx, strict=False)
                    if not raw_lines and isinstance(record, dict):
                        raw_lines = record.get(ds_name)

                if raw_lines:
                    # Convert items to row_data_list
                    for idx, line_item in enumerate(raw_lines, start=1):
                        line_ctx = dict(ctx)
                        line_ctx["line"] = line_item
                        line_ctx["idx"] = idx

                        row_dict = {}
                        if ds_def and hasattr(ds_def, "column_ids") and ds_def.column_ids:
                            for col in ds_def.column_ids:
                                val = evaluate_expression(col.expr, line_ctx, strict=strict)
                                row_dict[col.key] = val
                        else:
                            for key in lr.columns.values():
                                if isinstance(line_item, dict):
                                    row_dict[key] = line_item.get(key)
                                else:
                                    val = resolve_path(line_item, key)
                                    if val is None and hasattr(line_item, key):
                                        val = getattr(line_item, key)
                                    row_dict[key] = val
                        row_data_list.append(row_dict)

            # Expand and fill loop rows
            delta = expand_loop_row(ws, loop_row=lr, count=len(row_data_list), policy=policy)
            fill_loop_rows(ws, loop_row=lr, count=len(row_data_list), row_data_list=row_data_list)

        # 3b. Process image placeholders
        for c in scan.cells:
            if c.kind == "image":
                img_data = evaluate_expression(c.expr, ctx, strict=strict, cell_ref=c.coordinate)
                insert_image_into_cell(ws, c.coordinate, img_data)

        # 3c. Rescan sheet for remaining scalar placeholders
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "${" in cell.value:
                    val = cell.value
                    matches = list(re.finditer(r"\$\{([^}]+)\}", val))
                    if not matches:
                        continue
                    trimmed = val.strip()
                    # Whole cell replacement: preserve data type (int, float, Decimal, date)
                    if len(matches) == 1 and matches[0].span() == (0, len(trimmed)):
                        expr_token = matches[0].group(1).strip()
                        if not expr_token.startswith("table:") and not expr_token.startswith("image:"):
                            res = evaluate_expression(expr_token, ctx, strict=strict, cell_ref=cell.coordinate)
                            is_html_val = is_html(res)
                            cell.value = to_cell_value(res)
                            if isinstance(cell.value, str) and ("\n" in cell.value or is_html_val):
                                ensure_cell_wrap_text(cell)
                    else:
                        new_val = val
                        had_html = False
                        for m in matches:
                            expr_token = m.group(1).strip()
                            if not expr_token.startswith("table:") and not expr_token.startswith("image:"):
                                res = evaluate_expression(expr_token, ctx, strict=strict, cell_ref=cell.coordinate)
                                if is_html(res):
                                    had_html = True
                                new_val = new_val.replace(m.group(0), str(to_cell_value(res)))
                        cell.value = new_val
                        if isinstance(cell.value, str) and ("\n" in cell.value or had_html):
                            ensure_cell_wrap_text(cell)

    # 4. Set calculation on load flag
    wb.calculation.fullCalcOnLoad = True

    # 5. Save to bytes
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def render_report(template_bytes: bytes, record: Any, strict: bool = False) -> bytes:
    """
    Convenience interface matching PROJECT.md interface contract.
    """
    return render_template(template_bytes, record, strict=strict)
