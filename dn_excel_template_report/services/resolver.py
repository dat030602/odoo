# -*- coding: utf-8 -*-
"""Resolver service for dot-path traversal and openpyxl cell value conversion."""

import datetime
from decimal import Decimal
import html as html_lib
import re
from typing import Any, Dict, Optional

try:
    from odoo.tools import html2plaintext
except ImportError:
    html2plaintext = None

# Standard Odoo field path aliases
PATH_ALIASES: Dict[str, str] = {
    "address": "contact_address",
    "street_address": "contact_address",
    "notes": "note",
    "note": "notes",
}

HTML_TAG_RE = re.compile(
    r"<\s*/?\s*(?:p|div|br|span|ul|ol|li|h[1-6]|table|tr|td|th|tbody|thead|tfoot|b|strong|i|em|u|s|strike|a|font|section|header|footer|blockquote|pre|code|hr|body|html)\b[^>]*>",
    re.IGNORECASE,
)


def is_html(val: Any) -> bool:
    """Returns True if the string contains HTML markup tags."""
    if not isinstance(val, str) or not val:
        return False
    return bool("<" in val and ">" in val and HTML_TAG_RE.search(val))


def normalize_html(val: str) -> str:
    """
    Transforms HTML strings into clean plaintext.
    Converts <p>, <div>, <li>, <br> into line breaks, unescapes HTML entities,
    trims whitespace per line, and eliminates empty lines.
    """
    if not val:
        return ""

    # 1. If running within Odoo runtime, use html2plaintext with pre-normalized block tags
    if html2plaintext is not None:
        try:
            pre = re.sub(r"(?i)</(?:div|li)>", "\n", val)
            res = html2plaintext(pre)
            res = res.replace("\xa0", " ")
            lines = [line.strip() for line in res.splitlines()]
            return "\n".join([line for line in lines if line])
        except Exception:
            pass

    # 2. Pure-Python Zero-Dependency Fallback
    text = re.sub(r"(?i)<br\s*/?>", "\n", val)
    text = re.sub(r"(?i)</(?:p|div|li|tr|h[1-6])>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join([line for line in lines if line])


def resolve_path(target: Any, path: str) -> Any:
    """
    Safely traverses dot-separated paths on dicts, objects, or Odoo recordsets.
    Applies PATH_ALIASES on intermediate segments.
    Returns None if any intermediate segment evaluates to None or False.

    Args:
        target: Root object, dictionary, or Odoo record
        path: Dot-separated path string (e.g. "partner_id.address")

    Returns:
        Resolved value or None
    """
    if not target or not path:
        return None
    val = target
    for raw_part in path.split("."):
        if val is None or val is False:
            return None
        part = raw_part.strip()
        aliased = PATH_ALIASES.get(part, part)
        if isinstance(val, dict):
            if part in val:
                val = val[part]
            elif aliased in val:
                val = val[aliased]
            else:
                val = None
        else:
            try:
                if hasattr(val, part):
                    val = getattr(val, part)
                elif hasattr(val, aliased):
                    val = getattr(val, aliased)
                else:
                    val = None
            except Exception:
                return None
    return val


def resolve_field_path(record: Any, path: str) -> Any:
    """Alias for resolve_path to match architectural convention."""
    return resolve_path(record, path)


def to_cell_value(val: Any) -> Any:
    """
    Converts Odoo ORM / Python values into native openpyxl-compatible cell values.
    
    Rules:
        - False / None -> "" (Crucial: prevents Odoo unset fields rendering as 'FALSE' in Excel)
        - bool (True) -> True
        - int, float -> numeric value preserved
        - Decimal -> float
        - date, datetime, time -> preserved
        - Odoo recordset -> single display_name or comma-joined display_names
        - HTML string -> clean plaintext
        - fallback -> str(val)

    Args:
        val: Value to convert

    Returns:
        Openpyxl compatible value
    """
    if val is None or val is False:
        return ""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime.date, datetime.datetime, datetime.time)):
        return val

    # Odoo recordset detection
    if hasattr(val, "_name") and hasattr(val, "display_name"):
        try:
            length = len(val)
            if length == 0:
                return ""
            if length == 1:
                return to_cell_value(val.display_name or "")
            if hasattr(val, "mapped"):
                return ", ".join(to_cell_value(n) for n in val.mapped("display_name"))
            return ", ".join(to_cell_value(str(r.display_name or "")) for r in val)
        except Exception:
            return getattr(val, "display_name", "") or str(val)

    if hasattr(val, "display_name"):
        return to_cell_value(getattr(val, "display_name", "") or "")

    str_val = str(val)
    if is_html(str_val):
        return normalize_html(str_val)

    return str_val
