# -*- coding: utf-8 -*-
"""Image service for embedding and proportionally scaling images in openpyxl worksheets."""

import base64
import io
import logging
from typing import Any, Optional, Tuple, Union

from PIL import Image as PILImage
from openpyxl.drawing.image import Image as OpenpyxlImage
import openpyxl.utils

_logger = logging.getLogger(__name__)


def get_col_width_pixels(ws: Any, col_letter: str) -> int:
    """
    Calculates column width in pixels at standard 96 DPI.
    Default openpyxl/Excel character width is 8.43 chars.
    """
    w = None
    if col_letter in ws.column_dimensions:
        w = ws.column_dimensions[col_letter].width
    if w is None:
        w = 8.43
    return int(w * 7.5 + 5)


def get_row_height_pixels(ws: Any, row_idx: int) -> int:
    """
    Calculates row height in pixels at standard 96 DPI (1 pt = 4/3 px).
    Default openpyxl/Excel row height is 15.0 pt.
    """
    h = None
    if row_idx in ws.row_dimensions:
        h = ws.row_dimensions[row_idx].height
    if h is None:
        h = 15.0
    return int(h * (96.0 / 72.0))


def get_cell_box_pixels(ws: Any, coordinate: str) -> Tuple[int, int]:
    """
    Computes available bounding box in pixels for a cell coordinate.
    If the cell is part of a merged range, aggregates the width and height
    across all spanned columns and rows.

    Args:
        ws: openpyxl Worksheet instance
        coordinate: Cell coordinate (e.g. "A1" or "B2")

    Returns:
        Tuple of (width_px, height_px)
    """
    col_idx, row_idx = openpyxl.utils.coordinate_to_tuple(coordinate)

    target_range = None
    for mr in ws.merged_cells.ranges:
        if coordinate in mr:
            target_range = mr
            break

    if target_range:
        total_w = sum(
            get_col_width_pixels(ws, openpyxl.utils.get_column_letter(c))
            for c in range(target_range.min_col, target_range.max_col + 1)
        )
        total_h = sum(
            get_row_height_pixels(ws, r)
            for r in range(target_range.min_row, target_range.max_row + 1)
        )
    else:
        total_w = get_col_width_pixels(ws, openpyxl.utils.get_column_letter(col_idx))
        total_h = get_row_height_pixels(ws, row_idx)

    return max(total_w, 10), max(total_h, 10)


def insert_image_into_cell(
    ws: Any,
    coordinate: str,
    image_data: Union[bytes, str, None],
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
) -> None:
    """
    Decodes an image (binary or base64), scales it proportionally within the cell's
    bounding box (preserving aspect ratio and padding with 4% margin), anchors it at
    coordinate, and clears placeholder text from the cell.

    Args:
        ws: openpyxl Worksheet instance
        coordinate: Top-left cell coordinate string (e.g. "A1")
        image_data: Raw image bytes or base64-encoded string
        max_width: Optional explicit maximum width override in pixels
        max_height: Optional explicit maximum height override in pixels
    """
    if not image_data:
        ws[coordinate].value = None
        return

    # Decode binary
    try:
        if isinstance(image_data, str):
            # Strip potential data URL prefix
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            raw_bytes = base64.b64decode(image_data)
        elif isinstance(image_data, bytes):
            raw_bytes = image_data
        else:
            ws[coordinate].value = None
            return

        # Inspect dimensions via PIL
        pil_img = PILImage.open(io.BytesIO(raw_bytes))
        orig_w, orig_h = pil_img.size
        if orig_w <= 0 or orig_h <= 0:
            ws[coordinate].value = None
            return

        # Compute cell bounding box
        box_w, box_h = get_cell_box_pixels(ws, coordinate)

        # 4% padding margin
        pad_w = max(int(box_w * 0.04), 2)
        pad_h = max(int(box_h * 0.04), 2)
        avail_w = max(box_w - (pad_w * 2), 5)
        avail_h = max(box_h - (pad_h * 2), 5)

        if max_width:
            avail_w = min(avail_w, max_width)
        if max_height:
            avail_h = min(avail_h, max_height)

        # Proportional aspect ratio scaling
        scale = min(avail_w / orig_w, avail_h / orig_h)
        new_w = max(int(orig_w * scale), 1)
        new_h = max(int(orig_h * scale), 1)

        # Create openpyxl Image
        xl_img = OpenpyxlImage(io.BytesIO(raw_bytes))
        xl_img.width = new_w
        xl_img.height = new_h
        xl_img.anchor = coordinate

        ws.add_image(xl_img)
        ws[coordinate].value = None
    except Exception as e:
        _logger.warning("Failed to insert image at cell %s: %s", coordinate, e)
        ws[coordinate].value = None


def insert_image(
    ws: Any,
    coordinate: str,
    image_bytes_or_b64: Union[bytes, str, None],
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
) -> None:
    """Alias for insert_image_into_cell matching interface specification."""
    insert_image_into_cell(ws, coordinate, image_bytes_or_b64, max_width=max_width, max_height=max_height)
