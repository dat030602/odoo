# -*- coding: utf-8 -*-
"""Parser service for template cell placeholders and loop row discovery."""

import re
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import openpyxl.utils

PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


@dataclass
class Placeholder:
    """Represents a single placeholder expression parsed from a cell string."""
    raw: str
    token: str
    kind: str  # "table" | "image" | "expr"
    datasource: Optional[str] = None
    column_key: Optional[str] = None
    expr: Optional[str] = None


class ParsedCell(namedtuple("ParsedCell", ("row", "col", "kind", "expr", "whole_cell"))):
    """Represents a parsed cell containing dynamic placeholders."""

    @property
    def coordinate(self) -> str:
        """Returns the A1-style cell coordinate."""
        return f"{openpyxl.utils.get_column_letter(self.col)}{self.row}"

    @property
    def is_table_cell(self) -> bool:
        """True if this placeholder is a table column loop item."""
        return self.kind == "table"

    @property
    def is_image_cell(self) -> bool:
        """True if this placeholder is an image expression."""
        return self.kind == "image"


class LoopRow(namedtuple("LoopRow", ("row", "datasource", "columns"))):
    """Represents a worksheet row designated for table expansion."""

    @property
    def column_keys(self) -> Dict[int, str]:
        """Alias to `columns` dictionary mapping column index to column key."""
        return self.columns


SheetScan = namedtuple("SheetScan", ("cells", "loop_rows"))


class TemplateError(Exception):
    """Exception raised for invalid template placeholder syntax or structure."""

    def __init__(self, message: str, sheet_name: Optional[str] = None, row: Optional[int] = None, col: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.sheet_name = sheet_name
        self.row = row
        self.col = col

    def __str__(self) -> str:
        parts = []
        if self.sheet_name:
            parts.append(f"Sheet '{self.sheet_name}'")
        if self.row:
            parts.append(f"Row {self.row}")
        if self.col:
            parts.append(f"Col {self.col}")
        prefix = f"[{': '.join(parts)}] " if parts else ""
        return f"{prefix}{self.message}"


def classify(expr: str) -> Tuple[str, Any]:
    """
    Classifies a placeholder expression into kind and payload.

    Args:
        expr: Expression string inside ${...}

    Returns:
        Tuple of (kind, payload):
        - ("image", path_expression)
        - ("table", (datasource_name, column_key))
        - ("expr", scalar_expression)

    Raises:
        TemplateError: If table placeholder syntax is malformed.
    """
    expr = expr.strip()
    if expr.startswith("image:"):
        return ("image", expr[6:].strip())
    if expr.startswith("table:"):
        parts = expr[6:].strip().split(".", 1)
        if len(parts) != 2:
            raise TemplateError(
                f"Invalid table placeholder format '${{table:{expr[6:]}}}'. Expected 'datasource.column'"
            )
        datasource, key = parts
        return ("table", (datasource.strip(), key.strip()))
    return ("expr", expr)


def parse_cell(cell: Any) -> List[ParsedCell]:
    """
    Parses an openpyxl cell and extracts all valid placeholders.

    Args:
        cell: openpyxl Cell instance

    Returns:
        List of ParsedCell instances (empty if no placeholders or if formula cell)
    """
    if getattr(cell, "data_type", None) == "f" or not isinstance(getattr(cell, "value", None), str):
        return []
    val = cell.value
    matches = list(PLACEHOLDER.finditer(val))
    if not matches:
        return []

    parsed = []
    trimmed_val = val.strip()
    is_single_whole = len(matches) == 1 and matches[0].span() == (0, len(trimmed_val))

    for match in matches:
        kind, payload = classify(match.group(1))
        parsed.append(
            ParsedCell(
                row=cell.row,
                col=cell.column,
                kind=kind,
                expr=payload,
                whole_cell=is_single_whole,
            )
        )
    return parsed


def scan_sheet(ws: Any) -> SheetScan:
    """
    Scans an openpyxl worksheet, identifies all cell placeholders,
    validates table rows, and aggregates loop rows.

    Args:
        ws: openpyxl Worksheet instance

    Returns:
        SheetScan namedtuple with `cells` (list of ParsedCell) and `loop_rows` (dict of row_idx -> LoopRow).

    Raises:
        TemplateError: If a row contains multiple conflicting datasources.
    """
    all_cells: List[ParsedCell] = []
    table_rows: Dict[int, Dict[str, Any]] = {}

    for row in ws.iter_rows():
        for cell in row:
            parsed_cells = parse_cell(cell)
            if not parsed_cells:
                continue
            all_cells.extend(parsed_cells)
            for p in parsed_cells:
                if p.kind == "table":
                    ds, key = p.expr
                    if cell.row not in table_rows:
                        table_rows[cell.row] = {
                            "datasource": ds,
                            "columns": {cell.column: key},
                        }
                    else:
                        existing_ds = table_rows[cell.row]["datasource"]
                        if existing_ds != ds:
                            raise TemplateError(
                                f"Row {cell.row} contains multiple datasources: '{existing_ds}' and '{ds}'",
                                sheet_name=ws.title,
                                row=cell.row,
                                col=cell.column,
                            )
                        table_rows[cell.row]["columns"][cell.column] = key

    loop_rows = {
        row: LoopRow(row=row, datasource=data["datasource"], columns=data["columns"])
        for row, data in table_rows.items()
    }
    return SheetScan(cells=all_cells, loop_rows=loop_rows)


def scan_worksheet(ws: Any) -> Tuple[List[LoopRow], List[ParsedCell], List[ParsedCell]]:
    """
    Alternative scanning helper returning categorized collections.

    Args:
        ws: openpyxl Worksheet instance

    Returns:
        Tuple of (loop_rows_list, table_cells, scalar_cells)
    """
    scan = scan_sheet(ws)
    loop_rows = list(scan.loop_rows.values())
    table_cells = [c for c in scan.cells if c.kind == "table"]
    scalar_cells = [c for c in scan.cells if c.kind in ("expr", "image")]
    return loop_rows, table_cells, scalar_cells


def validate_template_sheet(ws: Any) -> List[str]:
    """
    Validates sheet placeholders and returns a list of error message strings.

    Args:
        ws: openpyxl Worksheet instance

    Returns:
        List of validation error messages (empty list if clean)
    """
    errors: List[str] = []
    try:
        scan_sheet(ws)
    except TemplateError as e:
        errors.append(str(e))
    except Exception as e:
        errors.append(f"Unexpected error validating sheet '{getattr(ws, 'title', '')}': {e}")
    return errors
