# -*- coding: utf-8 -*-
"""Formula adjustment and translation service for openpyxl worksheets."""

import re
from typing import Any, Tuple

from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.formula.translate import Translator

CELL_REF_RE = re.compile(r"^(\$?[A-Za-z]+)(\$?[0-9]+)$")


def translate_cell_formula(formula: str, origin_cell: str, target_cell: str) -> str:
    """
    Translates relative formula coordinates from origin_cell to target_cell.
    Preserves absolute row/column coordinates ($).

    Args:
        formula: Formula string (e.g. "=F19*H19")
        origin_cell: Source cell coordinate (e.g. "I19")
        target_cell: Destination cell coordinate (e.g. "I20")

    Returns:
        Translated formula string (e.g. "=F20*H20")
    """
    if not formula or not str(formula).startswith("="):
        return formula
    try:
        return Translator(formula, origin=origin_cell).translate_formula(target_cell)
    except Exception:
        return formula


def replicate_loop_formula(formula: str, src_coord: str, dst_coord: str) -> str:
    """Alias for translate_cell_formula to support architectural naming."""
    return translate_cell_formula(formula, src_coord, dst_coord)


def shift_range(min_row: int, max_row: int, loop_row: int, delta: int) -> Tuple[int, int]:
    """
    Shifts or expands a row interval [min_row, max_row] relative to loop_row expansion.

    Args:
        min_row: Starting row of interval
        max_row: Ending row of interval
        loop_row: Row index where loop expansion occurred
        delta: Row shift amount (+N or -1)

    Returns:
        Tuple of (new_min_row, new_max_row)
    """
    if min_row > loop_row:
        return (min_row + delta, max_row + delta)
    if min_row <= loop_row <= max_row:
        return (min_row, max(min_row, max_row + delta))
    return (min_row, max_row)


def adjust_endpoint(
    cell_str: str,
    loop_row: int,
    delta: int,
    is_range_end: bool = False,
    in_range_at_loop: bool = False,
) -> str:
    """
    Adjusts a single cell coordinate string (e.g. 'I19' or '$H$2') based on loop_row expansion.
    """
    m = CELL_REF_RE.match(cell_str)
    if not m:
        return cell_str
    col_str, row_str = m.group(1), m.group(2)
    has_row_abs = row_str.startswith("$")
    row_num = int(row_str.lstrip("$"))

    # Absolute row references are fixed
    if has_row_abs:
        return cell_str

    if in_range_at_loop and is_range_end:
        # Spanning range boundary expansion: e.g. I19:I19 -> I19:I21
        new_row = max(1, row_num + delta)
    elif row_num > loop_row:
        new_row = max(1, row_num + delta)
    else:
        new_row = row_num

    return f"{col_str}{new_row}"


def adjust_formula_for_shift(formula: str, loop_row: int, delta: int) -> str:
    """
    Tokenizes and adjusts cell and range references in a formula after loop_row expands/contracts.
    Detects ranges spanning loop_row (e.g. =SUM(I19:I19)) and expands the range boundary (=SUM(I19:I21)).

    Args:
        formula: Formula string
        loop_row: Index of the loop row
        delta: Row shift amount

    Returns:
        Adjusted formula string
    """
    if not formula or not str(formula).startswith("="):
        return formula

    try:
        tok = Tokenizer(formula)
    except Exception:
        return formula

    output_parts = ["="] if str(formula).startswith("=") else []

    for t in tok.items:
        if t.type == "OPERAND" and t.subtype == "RANGE":
            val = t.value
            prefix = ""
            if "!" in val:
                prefix, val = val.split("!", 1)
                prefix += "!"

            if ":" in val:
                parts = val.split(":", 1)
                start_c, end_c = parts[0], parts[1]
                m_start = CELL_REF_RE.match(start_c)
                m_end = CELL_REF_RE.match(end_c)
                if m_start and m_end:
                    start_r = int(m_start.group(2).lstrip("$"))
                    end_r = int(m_end.group(2).lstrip("$"))
                    in_range = (start_r <= loop_row <= end_r)
                    new_start = adjust_endpoint(start_c, loop_row, delta, is_range_end=False)
                    new_end = adjust_endpoint(end_c, loop_row, delta, is_range_end=True, in_range_at_loop=in_range)
                    val = f"{new_start}:{new_end}"
            else:
                val = adjust_endpoint(val, loop_row, delta)

            output_parts.append(f"{prefix}{val}")
        else:
            output_parts.append(t.value)

    return "".join(output_parts)


def expand_formula_ranges(formula: str, loop_row: int, delta: int) -> str:
    """Alias for adjust_formula_for_shift to match interface specification."""
    return adjust_formula_for_shift(formula, loop_row, delta)


def adjust_all_formulas(ws: Any, loop_row: int, delta: int) -> None:
    """
    Adjusts all formulas in a worksheet after a loop row expansion or contraction.
    Ignores formulas that are on the newly created duplicated loop rows (handled separately).

    Args:
        ws: openpyxl Worksheet instance
        loop_row: Row index of the loop row
        delta: Row shift amount
    """
    if delta == 0:
        return

    # Check all cells that have formula
    for row in ws.iter_rows():
        for cell in row:
            if getattr(cell, "data_type", None) == "f" or (
                isinstance(getattr(cell, "value", None), str) and cell.value.startswith("=")
            ):
                # Only adjust formulas that are outside the loop expansion range [loop_row, loop_row + delta]
                # unless delta < 0 (row deleted)
                if delta > 0 and loop_row <= cell.row <= loop_row + delta:
                    continue
                cell.value = adjust_formula_for_shift(cell.value, loop_row, delta)
