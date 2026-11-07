# -*- coding: utf-8 -*-
"""Layout expansion service for openpyxl worksheets.

Handles bottom-up loop row expansion, row insertion/deletion, metadata capture,
border preservation, merge coordinate shifting, conditional formatting rebuild,
and row height preservation.
"""

from collections import OrderedDict
import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from openpyxl.formatting.formatting import ConditionalFormatting
from openpyxl.formula.translate import Translator
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange

from .formula import adjust_all_formulas, adjust_formula_for_shift
from .resolver import is_html, to_cell_value


def expand_loop_row(
    ws: Any,
    loop_row: Any,
    count: int,
    policy: str = "keep_blank",
) -> int:
    """
    Expands a template loop row at loop_row to accommodate `count` data items.
    Preserves styling, borders, merges, conditional formatting, and row heights.

    Delta calculation:
      - count >= 1: count - 1
      - count == 0 and policy == 'keep_blank': 0
      - count == 0 and policy == 'remove': -1

    Args:
        ws: openpyxl Worksheet instance
        loop_row: Integer row index (1-based) or LoopRow instance
        count: Number of data items to accommodate (>= 0)
        policy: 'keep_blank' | 'remove' (behavior when count == 0)

    Returns:
        The delta (net rows added/removed).
    """
    R = loop_row.row if hasattr(loop_row, "row") else int(loop_row)

    # Cache columns from row R for fill_loop_rows
    if not hasattr(ws, "_loop_columns_cache"):
        ws._loop_columns_cache = {}
    if hasattr(loop_row, "columns"):
        ws._loop_columns_cache[R] = loop_row.columns
    elif hasattr(loop_row, "column_keys"):
        ws._loop_columns_cache[R] = loop_row.column_keys
    elif R not in ws._loop_columns_cache:
        col_map = {}
        for c in range(1, ws.max_column + 1):
            val = ws.cell(row=R, column=c).value
            if isinstance(val, str):
                m = re.search(r"\$\{table:[^.]+\.([^}]+)\}", val)
                if m:
                    col_map[c] = m.group(1).strip()
        if col_map:
            ws._loop_columns_cache[R] = col_map

    # 1. Delta Calculation
    if count >= 1:
        delta = count - 1
    elif policy == "remove":
        delta = -1
    else:
        delta = 0

    # If no structural row change is required, return immediately
    if delta == 0:
        return 0

    # 2. Deletion branch (count == 0, policy == 'remove', delta == -1)
    if delta == -1:
        # Phase 1: Capture metadata
        saved_merges = list(ws.merged_cells.ranges)
        ws.merged_cells.ranges.clear()  # Clear without calling destructive unmerge_cells()

        saved_cf_rules = OrderedDict(ws.conditional_formatting._cf_rules)
        ws.conditional_formatting._cf_rules.clear()

        saved_row_dims = {
            r: ws.row_dimensions[r].height
            for r in list(ws.row_dimensions.keys())
            if ws.row_dimensions[r].height is not None
        }

        # Phase 2: Delete row
        ws.delete_rows(R, amount=1)

        # Phase 3: Restore shifted merges
        for mr in saved_merges:
            if mr.max_row < R:
                ws.merged_cells.add(mr)
            elif mr.min_row == R and mr.max_row == R:
                # Merge was on deleted row, omit
                continue
            elif mr.min_row > R:
                ws.merged_cells.add(
                    CellRange(
                        min_col=mr.min_col,
                        min_row=mr.min_row - 1,
                        max_col=mr.max_col,
                        max_row=mr.max_row - 1,
                    )
                )
            elif mr.min_row <= R <= mr.max_row:
                if mr.max_row - 1 >= mr.min_row:
                    ws.merged_cells.add(
                        CellRange(
                            min_col=mr.min_col,
                            min_row=mr.min_row,
                            max_col=mr.max_col,
                            max_row=mr.max_row - 1,
                        )
                    )

        # Phase 4: Restore shifted Conditional Formatting (hash safe)
        new_cf_rules = OrderedDict()
        for cf, rules in saved_cf_rules.items():
            new_ranges = []
            for cr in cf.sqref.ranges:
                if cr.max_row < R:
                    new_ranges.append(cr)
                elif cr.min_row > R:
                    new_ranges.append(
                        CellRange(
                            min_col=cr.min_col,
                            min_row=cr.min_row - 1,
                            max_col=cr.max_col,
                            max_row=cr.max_row - 1,
                        )
                    )
                else:
                    if cr.max_row - 1 >= cr.min_row:
                        new_ranges.append(
                            CellRange(
                                min_col=cr.min_col,
                                min_row=cr.min_row,
                                max_col=cr.max_col,
                                max_row=cr.max_row - 1,
                            )
                        )
            if new_ranges:
                new_cf = ConditionalFormatting(sqref=MultiCellRange(new_ranges), pivot=getattr(cf, "pivot", None))
                new_cf_rules[new_cf] = rules
        ws.conditional_formatting._cf_rules = new_cf_rules

        # Phase 5: Restore shifted Row Dimensions
        for r in list(ws.row_dimensions.keys()):
            del ws.row_dimensions[r]
        for r, h in saved_row_dims.items():
            if r < R:
                ws.row_dimensions[r].height = h
            elif r > R:
                ws.row_dimensions[r - 1].height = h

        # Phase 6: Adjust formulas
        adjust_all_formulas(ws, loop_row=R, delta=-1)

        return -1

    # 3. Expansion branch (count > 1, delta > 0)
    # Phase 1: Capture metadata
    saved_merges = list(ws.merged_cells.ranges)
    ws.merged_cells.ranges.clear()  # Preserve slave cell borders

    saved_cf_rules = OrderedDict(ws.conditional_formatting._cf_rules)
    ws.conditional_formatting._cf_rules.clear()  # Avoid OrderedDict hash corruption

    saved_row_dims = {
        r: ws.row_dimensions[r].height
        for r in list(ws.row_dimensions.keys())
        if ws.row_dimensions[r].height is not None
    }
    template_height = saved_row_dims.get(R)

    # Phase 2: Insert rows
    ws.insert_rows(R + 1, amount=delta)

    # Phase 3: Duplicate template row styling & relative formulas
    max_c = ws.max_column
    for k in range(1, count):
        curr_row = R + k
        for c in range(1, max_c + 1):
            src = ws.cell(row=R, column=c)
            dst = ws.cell(row=curr_row, column=c)
            # copy.copy avoids mutable StyleArray sharing (Quirk 3)
            dst._style = copy.copy(src._style)
            if src.value and str(src.value).startswith("="):
                src_coord = f"{get_column_letter(c)}{R}"
                dst_coord = f"{get_column_letter(c)}{curr_row}"
                dst.value = Translator(src.value, origin=src_coord).translate_formula(dst_coord)
            else:
                dst.value = src.value

    # Phase 4: Restore and shift Merges (Quirk 1 & Quirk 2)
    for mr in saved_merges:
        if mr.max_row < R:
            ws.merged_cells.add(mr)
        elif mr.min_row == R and mr.max_row == R:
            # Clone template row merge across all duplicated rows
            for k in range(count):
                ws.merged_cells.add(
                    CellRange(
                        min_col=mr.min_col,
                        min_row=R + k,
                        max_col=mr.max_col,
                        max_row=R + k,
                    )
                )
        elif mr.min_row <= R <= mr.max_row:
            # Range spans R: expand boundary
            ws.merged_cells.add(
                CellRange(
                    min_col=mr.min_col,
                    min_row=mr.min_row,
                    max_col=mr.max_col,
                    max_row=mr.max_row + delta,
                )
            )
        elif mr.min_row > R:
            # Range strictly below R: shift by delta
            ws.merged_cells.add(
                CellRange(
                    min_col=mr.min_col,
                    min_row=mr.min_row + delta,
                    max_col=mr.max_col,
                    max_row=mr.max_row + delta,
                )
            )

    # Phase 5: Restore and shift Conditional Formatting (Quirk 4)
    new_cf_rules = OrderedDict()
    for cf, rules in saved_cf_rules.items():
        new_ranges = []
        for cr in cf.sqref.ranges:
            if cr.max_row < R:
                new_ranges.append(cr)
            elif cr.min_row > R:
                new_ranges.append(
                    CellRange(
                        min_col=cr.min_col,
                        min_row=cr.min_row + delta,
                        max_col=cr.max_col,
                        max_row=cr.max_row + delta,
                    )
                )
            else:
                new_ranges.append(
                    CellRange(
                        min_col=cr.min_col,
                        min_row=cr.min_row,
                        max_col=cr.max_col,
                        max_row=cr.max_row + delta,
                    )
                )
        new_cf = ConditionalFormatting(sqref=MultiCellRange(new_ranges), pivot=getattr(cf, "pivot", None))
        new_cf_rules[new_cf] = rules
    ws.conditional_formatting._cf_rules = new_cf_rules

    # Phase 6: Restore and shift Row Dimensions
    for r in list(ws.row_dimensions.keys()):
        del ws.row_dimensions[r]
    for r, h in saved_row_dims.items():
        if r < R:
            ws.row_dimensions[r].height = h
        elif r == R:
            ws.row_dimensions[r].height = h
            for k in range(1, count):
                ws.row_dimensions[r + k].height = h
        else:
            ws.row_dimensions[r + delta].height = h

    # Phase 7: Shift image anchors if any exist
    if hasattr(ws, "_images"):
        for img in ws._images:
            if isinstance(img.anchor, str):
                import openpyxl.utils
                c_col, c_row = openpyxl.utils.coordinate_to_tuple(img.anchor)
                if c_row > R:
                    img.anchor = f"{openpyxl.utils.get_column_letter(c_col)}{c_row + delta}"
            elif hasattr(img.anchor, "_from"):
                if img.anchor._from.row >= R:
                    img.anchor._from.row += delta
                if hasattr(img.anchor, "_to") and img.anchor._to.row >= R:
                    img.anchor._to.row += delta

    # Phase 8: Adjust all outside formulas and summary aggregates
    adjust_all_formulas(ws, loop_row=R, delta=delta)

    return delta


def ensure_cell_wrap_text(cell: Any) -> None:
    """
    Ensures that openpyxl cell alignment has wrap_text = True,
    safely cloning existing alignment to bypass StyleProxy immutability.
    """
    if getattr(cell, "alignment", None) is not None:
        align = copy.copy(cell.alignment)
        align.wrap_text = True
        cell.alignment = align
    else:
        cell.alignment = Alignment(wrap_text=True)


def fill_loop_rows(
    ws: Any,
    loop_row: Any,
    count: int,
    row_data_list: List[Dict[str, Any]],
    meta_merges: Optional[List[Tuple[int, int, int, int]]] = None,
) -> None:
    """
    Populates data, relative formulas, and cloned merges for an expanded loop row.

    Args:
        ws: openpyxl Worksheet instance
        loop_row: Integer row index (1-based) or LoopRow instance
        count: Number of data rows
        row_data_list: List of dictionaries mapping column keys to data values
        meta_merges: Optional list of (min_row, min_col, max_row, max_col) tuples
    """
    R = loop_row.row if hasattr(loop_row, "row") else int(loop_row)

    if count == 0:
        # Edge case N=0: Clear table placeholders on template row
        for c in range(1, ws.max_column + 1):
            cell = ws.cell(row=R, column=c)
            if isinstance(cell.value, str) and "${table:" in cell.value:
                cell.value = ""
        return

    # Determine column mapping
    col_mapping: Dict[int, str] = {}
    if hasattr(ws, "_loop_columns_cache") and R in ws._loop_columns_cache:
        col_mapping = ws._loop_columns_cache[R]
    elif hasattr(loop_row, "columns"):
        col_mapping = loop_row.columns
    elif hasattr(loop_row, "column_keys"):
        col_mapping = loop_row.column_keys
    else:
        for c in range(1, ws.max_column + 1):
            val = ws.cell(row=R, column=c).value
            if isinstance(val, str):
                m = re.search(r"\$\{table:[^.]+\.([^}]+)\}", val)
                if m:
                    col_mapping[c] = m.group(1).strip()

    # Capture template row cell formulas and styles before overwriting
    template_formulas: Dict[int, str] = {}
    template_styles: Dict[int, Any] = {}
    max_c = ws.max_column
    for c in range(1, max_c + 1):
        cell = ws.cell(row=R, column=c)
        template_styles[c] = cell._style
        if cell.value and str(cell.value).startswith("="):
            template_formulas[c] = cell.value

    # Populate rows
    for k in range(min(count, len(row_data_list))):
        curr_row = R + k
        row_dict = row_data_list[k]

        # Ensure style duplication for duplicated rows
        if k > 0:
            for c in range(1, max_c + 1):
                src_style = template_styles.get(c)
                if src_style is not None:
                    dst = ws.cell(row=curr_row, column=c)
                    dst._style = copy.copy(src_style)

                # Relative formula translation
                if c in template_formulas:
                    src_f = template_formulas[c]
                    src_coord = f"{get_column_letter(c)}{R}"
                    dst_coord = f"{get_column_letter(c)}{curr_row}"
                    ws.cell(row=curr_row, column=c).value = Translator(src_f, origin=src_coord).translate_formula(dst_coord)

        # Populate mapped data columns
        for col_idx, key in col_mapping.items():
            if key in row_dict:
                raw_val = row_dict[key]
                is_html_val = is_html(raw_val)
                cell = ws.cell(row=curr_row, column=col_idx)
                cell.value = to_cell_value(raw_val)
                if isinstance(cell.value, str) and ("\n" in cell.value or is_html_val):
                    ensure_cell_wrap_text(cell)

    # Ensure meta merges exist across loop rows
    if meta_merges:
        for m in meta_merges:
            min_r, min_c, max_r, max_c = m
            if min_r == R and max_r == R:
                for k in range(count):
                    cr = CellRange(min_col=min_c, min_row=R + k, max_col=max_c, max_row=R + k)
                    if cr not in ws.merged_cells.ranges:
                        ws.merged_cells.add(cr)
