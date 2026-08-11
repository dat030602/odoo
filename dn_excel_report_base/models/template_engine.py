# -*- coding: utf-8 -*-
"""
template_engine.py
==================

Pure-Python template engine for openpyxl worksheets.

This module is deliberately framework-agnostic — it operates on an
``openpyxl.Worksheet`` and a plain ``dict``/``list`` context, with zero
Odoo imports. This allows unit testing outside of an Odoo database.

Template Syntax:
----------------
    {{ path.to.value }}              Value substitution (dot-path resolution)
    {{ value | fmt:'#,##0.00' }}      Number/date formatting via cell.number_format
    {% for x in path %} ... {% endfor %}  Loop blocks (flat only in Giai đoạn 1)
    {% if expr %} ... {% endif %}    Conditional blocks
    {{ list_name | sum:'field' }}    =SUBTOTAL(9, ...) over expanded range
    {{ list_name | count:'field' }}  =SUBTOTAL(2, ...)
    {{ list_name | avg:'field' }}    =SUBTOTAL(1, ...)
    {{ list_name | max:'field' }}    =SUBTOTAL(4, ...)
    {{ list_name | min:'field' }}    =SUBTOTAL(5, ...)

Author: Dat Nguyen
"""

import re
import base64
import requests
from copy import copy
from dataclasses import dataclass, field
from typing import Any
from io import BytesIO

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.drawing.image import Image as OpenpyxlImage
from simpleeval import EvalWithCompoundTypes

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ─────────────────────────────────────────────────────────────────────────────
# REGEX PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

FOR_RE = re.compile(r'^\{%\s*for\s+(\w+)\s+in\s+([\w.]+)\s*%\}$')
ENDFOR_RE = re.compile(r'^\{%\s*endfor\s*%\}$')
IF_RE = re.compile(r'^\{%\s*if\s+(.+?)\s*%\}$')
ENDIF_RE = re.compile(r'^\{%\s*endif\s*%\}$')
PLACEHOLDER_RE = re.compile(r'\{\{\s*(.+?)\s*\}\}')

# Aggregate filter name → SUBTOTAL function code
AGG_FUNCS = {
    'sum': 9,
    'avg': 1,
    'count': 2,
    'max': 4,
    'min': 5,
}


# ─────────────────────────────────────────────────────────────────────────────
# EXCEPTIONS
# ─────────────────────────────────────────────────────────────────────────────

class TemplateError(Exception):
    """Raised for any template syntax or resolution error.

    Caught by the Odoo layer and re-raised as UserError with a friendly message.
    """


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Block:
    """Represents a parsed template block (for/if).

    Attributes:
        kind: 'for' or 'if'
        start_row: Row index of the opening marker ({% for %} / {% if %})
        end_row: Row index of the closing marker ({% endfor %} / {% endif %})
        var_name: Loop variable name (only for 'for' blocks)
        iter_path: Dot-path to the iterable in context (only for 'for' blocks)
        condition: Condition expression string (only for 'if' blocks)
        depth: Nesting depth (0 = top-level)
        children: Nested child blocks
    """
    kind: str
    start_row: int
    end_row: int
    var_name: str = ''
    iter_path: str = ''
    condition: str = ''
    depth: int = 0
    children: list = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class TemplateEngine:
    """Renders a template Worksheet in-place against a context dict.

    The engine processes the worksheet through the following pipeline:
        1. parse_blocks() — Find all {% for %} / {% if %} blocks using a stack
        2. expand() — Expand blocks recursively (deepest first)
        3. resolve_placeholders() — Replace remaining {{ }} placeholders
        4. resolve_sum_filters() — Convert aggregate filters to SUBTOTAL formulas
        5. embed_images() — Handle {{ x | image }} filters (Giai đoạn 3)

    Args:
        sheet: The openpyxl Worksheet to render (modified in-place).
        marker_column: Column index (1-based) where block markers are located.
                       Defaults to 1 (column A).
    """

    def __init__(self, sheet: Worksheet, marker_column: int = 1):
        self.sheet = sheet
        self.marker_column = marker_column
        # Populated during expand(); consumed by resolve_sum_filters()
        # Maps loop variable name → (start_row, end_row) of expanded data
        self.expanded_ranges: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def render(self, context: dict):
        """Render the template worksheet in-place against the given context.

        Args:
            context: A dict (possibly nested with lists/dicts) containing
                     all data needed to resolve placeholders and loops.

        Raises:
            TemplateError: On any syntax or resolution error.
        """
        blocks = self.parse_blocks()

        # Guard: nested for loops are not yet supported in Giai đoạn 1
        # (if blocks inside for blocks ARE supported)
        for block in blocks:
            for child in block.children:
                if child.kind == 'for':
                    raise TemplateError(
                        f"Nested for loops are not yet supported (Giai đoạn 2). "
                        f"Found nested for block inside row {block.start_row}."
                    )

        # Process top-level blocks only (children are handled during expansion)
        top_level_blocks = [b for b in blocks if b.depth == 0]
        # Sort by start_row descending so we process bottom-up,
        # avoiding row index shifts affecting unprocessed blocks above
        top_level_blocks.sort(key=lambda b: -b.start_row)

        for block in top_level_blocks:
            if block.kind == 'for':
                self.expand_for_block(block, context)
            elif block.kind == 'if':
                self.expand_if_block(block, context)

        self.resolve_placeholders(self.sheet, context)
        self.resolve_sum_filters(context)
        self.embed_images()

    # ------------------------------------------------------------------ #
    # 5.2  Block parsing
    # ------------------------------------------------------------------ #

    def parse_blocks(self) -> list[Block]:
        """Scan the marker column top-to-bottom, matching {% %} pairs with
        a stack so nested blocks parse correctly.

        Returns:
            List of top-level Block objects (with children populated for
            nested blocks).

        Raises:
            TemplateError: On unmatched, mismatched, or unclosed blocks.
        """
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
        """Expand a {% for %} block by duplicating its body for each item.

        Handles child {% if %} blocks within the loop body by evaluating
        them for each iteration. Child if blocks are processed per-copy
        with the loop variable in context.

        Args:
            block: The parsed for-block to expand.
            context: The current context dict.

        Raises:
            TemplateError: On empty loop body or resolution errors.
        """
        items = self.resolve_path(block.iter_path, context)
        if items is None:
            items = []
        items = list(items)

        body_start = block.start_row + 1
        body_end = block.end_row - 1
        body_height = body_end - body_start + 1

        if body_height < 1:
            raise TemplateError(
                f"Empty loop body for '{{% for {block.var_name} in "
                f"{block.iter_path} %}}' at row {block.start_row}."
            )

        n = len(items)
        if n == 0:
            # No data: delete the entire block (markers + body)
            self.sheet.delete_rows(
                block.start_row,
                amount=block.end_row - block.start_row + 1,
            )
            self.expanded_ranges[block.iter_path] = (block.start_row, block.start_row - 1)
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

        # Process each copy: resolve child {% if %} blocks and {{ }} placeholders
        # Process from bottom to top so row deletions don't affect unprocessed copies
        for copy_idx in range(n - 1, -1, -1):
            offset = copy_idx * body_height
            item_context = dict(context)
            item_context[block.var_name] = items[copy_idx]

            # Process child if blocks within this copy (bottom-up to handle shifts)
            for child_block in reversed(block.children):
                if child_block.kind == 'if':
                    child_start = child_block.start_row + offset
                    child_end = child_block.end_row + offset
                    self._expand_if_block_at(
                        child_start, child_end,
                        child_block.condition, item_context
                    )

            # Resolve {{ }} placeholders in each row of this copy
            for src_row in first_copy_rows:
                dst_row = src_row + offset
                self.resolve_placeholders(
                    self.sheet, item_context,
                    row_range=(dst_row, dst_row),
                )

        # Find the actual position of the {% endfor %} marker after all
        # child block processing (row numbers may have shifted)
        endfor_row = self._find_marker_row(block.end_row + extra_rows, ENDFOR_RE)

        # Delete the two marker rows themselves
        # Delete {% endfor %} first (higher row number), then {% for %}
        self.sheet.delete_rows(endfor_row, amount=1)
        self.sheet.delete_rows(block.start_row, amount=1)

        # Record the actual data range AFTER marker deletion
        # (body_start shifts up by 1 due to opening marker deletion)
        actual_start = body_start - 1
        actual_end = actual_start + n * body_height - 1
        self.expanded_ranges[block.iter_path] = (actual_start, actual_end)

    def _find_marker_row(self, start_row: int, pattern) -> int:
        """Find the row containing a marker matching the given pattern.

        Searches upward from start_row to find a row whose marker column
        cell matches the pattern.

        Args:
            start_row: Row to start searching from (searches upward).
            pattern: Compiled regex pattern to match.

        Returns:
            The row number of the matching marker.

        Raises:
            TemplateError: If no matching marker is found.
        """
        for row in range(start_row, 0, -1):
            cell = self.sheet.cell(row=row, column=self.marker_column)
            value = (cell.value or '').strip() if isinstance(cell.value, str) else ''
            if pattern.match(value):
                return row
        raise TemplateError(
            f"Could not locate marker row after expansion."
        )

    def expand_if_block(self, block: Block, context: dict):
        """Expand a {% if %} block by evaluating its condition.

        If the condition is True, the body is kept and only the two marker
        rows are deleted. If False, the entire block (markers + body) is
        deleted.

        Args:
            block: The parsed if-block to expand.
            context: The current context dict.

        Raises:
            TemplateError: If the condition cannot be evaluated.
        """
        self._expand_if_block_at(
            block.start_row, block.end_row, block.condition, context
        )

    def _expand_if_block_at(self, start_row: int, end_row: int,
                            condition: str, context: dict):
        """Expand an if-block at the given row positions.

        This is the core implementation shared by both top-level if blocks
        and if blocks nested inside for loops.

        Args:
            start_row: Row index of the {% if %} marker.
            end_row: Row index of the {% endif %} marker.
            condition: The condition expression string.
            context: The context dict for evaluation.

        Raises:
            TemplateError: If the condition cannot be evaluated.
        """
        try:
            evaluator = EvalWithCompoundTypes(names=context)
            result = bool(evaluator.eval(condition))
        except Exception as exc:
            raise TemplateError(
                f"Failed to evaluate condition '{condition}' at row "
                f"{start_row}: {exc}"
            ) from exc

        if result:
            # Keep body, drop the two marker rows
            self.sheet.delete_rows(end_row, amount=1)
            self.sheet.delete_rows(start_row, amount=1)
        else:
            # Delete entire block (markers + body)
            self.sheet.delete_rows(
                start_row,
                amount=end_row - start_row + 1,
            )

    def _copy_row(self, src_row: int, dst_row: int):
        """Clone values + styles from src_row to dst_row across all columns.

        Mirrors v1's _copy_row_styles() but also copies the raw {{ }} template
        text, since dst_row starts blank after insert_rows().

        Args:
            src_row: 1-based source row index.
            dst_row: 1-based destination row index.
        """
        max_col = self.sheet.max_column
        for col in range(1, max_col + 1):
            src = self.sheet.cell(row=src_row, column=col)
            dst = self.sheet.cell(row=dst_row, column=col)
            dst.value = src.value
            if src.has_style:
                dst.font = copy(src.font)
                dst.border = copy(src.border)
                dst.fill = copy(src.fill)
                dst.alignment = copy(src.alignment)
                dst.number_format = src.number_format
        # Row height
        if src_row in self.sheet.row_dimensions:
            self.sheet.row_dimensions[dst_row].height = \
                self.sheet.row_dimensions[src_row].height

    # ------------------------------------------------------------------ #
    # 5.4  Placeholder resolution
    # ------------------------------------------------------------------ #

    def resolve_placeholders(self, sheet: Worksheet, context: dict,
                             row_range: tuple[int, int] | None = None):
        """Resolve all {{ }} placeholders in the worksheet (or a row range).

        Args:
            sheet: The worksheet to process.
            context: The context dict for path resolution.
            row_range: Optional (start_row, end_row) tuple to limit processing.
                       If None, processes the entire sheet.
        """
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
        """Check if a cell value contains an aggregate filter expression.

        Args:
            text: The cell value string.

        Returns:
            True if the expression contains an aggregate filter (sum, count, etc.).
        """
        m = PLACEHOLDER_RE.search(text)
        if not m:
            return False
        expr = m.group(1)
        if '|' not in expr:
            return False
        filt = expr.split('|', 1)[1].strip()
        return filt.split(':', 1)[0].strip() in AGG_FUNCS

    def _render_cell_text(self, text: str, context: dict):
        """Render a cell's text by resolving all {{ }} placeholders within it.

        If the cell contains exactly one placeholder with no surrounding text,
        the original value type is preserved (int, float, date, etc.) instead
        of being coerced to string. The ``fmt`` filter sets the cell's
        number_format without converting the value to a string.

        Args:
            text: The cell value string containing placeholders.
            context: The context dict for path resolution.

        Returns:
            Tuple of (rendered_value, is_formula, number_format).
            rendered_value may be a non-string type if the cell contained
            a single bare placeholder.

        Raises:
            TemplateError: If the image filter is used (not supported in Giai đoạn 1).
        """
        number_format = None

        # Check if this is a single placeholder with only the fmt filter
        # (no surrounding text). In that case, preserve the original value type.
        # Supports both quoted ('#,##0.00') and unquoted (#,##0.00) format strings.
        single_fmt_match = re.fullmatch(
            r'\{\{\s*([\w.]+)\s*\|\s*fmt\s*:\s*(?:\'([^\']+)\'|([^\s}]+))\s*\}\}',
            text,
        )
        if single_fmt_match:
            path = single_fmt_match.group(1).strip()
            fmt = single_fmt_match.group(2) or single_fmt_match.group(3)
            value = self.resolve_path(path, context)
            if value is None:
                return '', False, None
            if isinstance(value, str) and value.startswith('='):
                return value, True, None
            return value, False, fmt

        # Check if this is a single bare placeholder (no surrounding text, no filters)
        # In that case, preserve the original value type
        single_match = re.fullmatch(r'\{\{\s*([\w.]+)\s*\}\}', text)
        if single_match:
            path = single_match.group(1).strip()
            value = self.resolve_path(path, context)
            if value is None:
                return '', False, None
            if isinstance(value, str) and value.startswith('='):
                return value, True, None
            return value, False, None

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
                    # Formatting applied via cell.number_format
                elif name == 'image':
                    # Return a marker that embed_images() will process later
                    # Handle bytes values (e.g. Odoo binary fields) by decoding
                    # to str so the marker doesn't contain b'...' repr
                    if isinstance(value, bytes):
                        value = value.decode('utf-8', errors='replace')
                    return f'__IMAGE__:{value}'
            return '' if value is None else str(value)

        rendered = PLACEHOLDER_RE.sub(_sub, text)
        is_formula = rendered.startswith('=')
        return rendered, is_formula, number_format

    # ------------------------------------------------------------------ #
    # 5.5  Sum / aggregate filters
    # ------------------------------------------------------------------ #

    def resolve_sum_filters(self, context: dict):
        """Convert aggregate filter expressions into SUBTOTAL formulas.

        Scans the entire sheet for {{ list_name | filter:'field' }} expressions
        and replaces them with =SUBTOTAL(code, col_start:col_end) formulas
        referencing the actual expanded row range of the corresponding loop.

        Args:
            context: The context dict (used for reference, though ranges are
                     already recorded in self.expanded_ranges).

        Raises:
            TemplateError: If an aggregate filter references an unknown loop variable.
        """
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
                    formula = 0  # Loop rendered zero rows — nothing to aggregate
                else:
                    formula = f'=SUBTOTAL({code},{col_letter}{start}:{col_letter}{end})'
                cell.value = formula

    # ------------------------------------------------------------------ #
    # 5.7  Image embedding
    # ------------------------------------------------------------------ #

    def embed_images(self):
        """Process all __IMAGE__ markers and embed actual images.

        Scans the worksheet for cells containing '__IMAGE__:' markers
        (set by _render_cell_text when the | image filter is used) and
        replaces them with actual openpyxl Image objects.

        Supports:
            - Base64-encoded image data
            - URLs (http/https)
            - Optional width/height resizing (via PIL if available)

        Images are anchored to their cell and the cell dimensions are
        adjusted to fit the image, providing "Place in Cell" behavior
        similar to xlsxwriter's embed_image().
        """
        for row in range(1, self.sheet.max_row + 1):
            for col in range(1, self.sheet.max_column + 1):
                cell = self.sheet.cell(row=row, column=col)
                if not isinstance(cell.value, str) or not cell.value.startswith('__IMAGE__:'):
                    continue

                image_data = cell.value[len('__IMAGE__:'):]
                img = self._load_image(image_data)
                if img:
                    self.sheet.add_image(img, cell.coordinate)
                    cell.value = None
                    # Adjust cell dimensions to fit the image ("Place in Cell")
                    self._fit_cell_to_image(row, col, img)

    def _load_image(self, image_data):
        """Load an image from base64 string or URL.

        Args:
            image_data: Base64-encoded image data or a URL string.

        Returns:
            An openpyxl Image object, or None if loading fails.
        """
        if not image_data:
            return None

        try:
            # Check if it's a URL
            if image_data.startswith(('http://', 'https://')):
                response = requests.get(image_data, timeout=30)
                response.raise_for_status()
                img_bytes = response.content
            else:
                # Assume base64
                img_bytes = base64.b64decode(image_data)

            # Create openpyxl image
            img = OpenpyxlImage(BytesIO(img_bytes))
            return img
        except Exception:
            return None

    def _fit_cell_to_image(self, row: int, col: int, img):
        """Adjust cell dimensions to fit an embedded image.

        Sets the row height and column width so the image fits within
        the cell, providing "Place in Cell" behavior.

        Args:
            row: 1-based row index of the cell.
            col: 1-based column index of the cell.
            img: The openpyxl Image object to fit.
        """
        # openpyxl stores image dimensions in pixels
        # Excel row height is in points (1 point = 1/72 inch)
        # Excel column width is in character units
        # Approximate conversion: 1 pixel ≈ 0.75 points for row height
        # Column width: 1 character ≈ 7-8 pixels (depends on font)
        img_width_px = img.width
        img_height_px = img.height

        # Set row height (points) to match image height
        # Default Excel font (Calibri 11) has ~15 pixels per row
        # 1 point = 1/72 inch, 1 pixel ≈ 0.75 points
        row_height_pt = img_height_px * 0.75
        self.sheet.row_dimensions[row].height = row_height_pt

        # Set column width (character units) to match image width
        # Approximate: 1 character width ≈ 7 pixels for default font
        col_width_chars = img_width_px / 7.0
        self.sheet.column_dimensions[get_column_letter(col)].width = col_width_chars

    # ------------------------------------------------------------------ #
    # 5.6  Path resolution
    # ------------------------------------------------------------------ #

    @staticmethod
    def resolve_path(path: str, context: dict) -> Any:
        """Resolve a dot-path against the context.

        Tries dict.get first, then getattr — works transparently with
        plain dicts, Odoo recordsets, or nested objects.

        Args:
            path: Dot-separated path (e.g. 'company.name' or 'line.partner.city').
            context: The context dict to resolve against.

        Returns:
            The resolved value, or None if any part of the path is missing.
        """
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
