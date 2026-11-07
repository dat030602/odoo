# -*- coding: utf-8 -*-
"""Evaluator service providing safe expression evaluation and evaluation context."""

import datetime
from decimal import Decimal
import logging
import time
from typing import Any, Dict, Optional

from .resolver import normalize_html, resolve_path, to_cell_value

_logger = logging.getLogger(__name__)

# Attempt to import Odoo safe_eval if running inside Odoo runtime
try:
    import odoo.tools.safe_eval as se
    safe_eval = se.safe_eval
    safe_datetime = getattr(se, "datetime", datetime)
    safe_time = getattr(se, "time", time)
except ImportError:
    se = None
    safe_eval = None
    safe_datetime = datetime
    safe_time = time


def build_eval_context(
    record: Any,
    records: Any = None,
    template: Any = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Constructs a rich evaluation context dictionary for template rendering.

    Args:
        record: Current primary Odoo record
        records: Recordset for batch/multi-record rendering
        template: Optional excel.report.template model record
        extra: Additional contextual variables (e.g. `line`, `idx`)

    Returns:
        Dictionary containing standard context variables and helper functions
    """
    env = getattr(record, "env", None)
    company = getattr(record, "company_id", None)
    if not company and env:
        company = getattr(env, "company", None)
    user = getattr(env, "user", None) if env else None

    # Safe date and amount formatters
    def _format_date(d: Any, fmt: Optional[str] = None) -> str:
        if not d:
            return ""
        if env:
            try:
                from odoo.tools import format_date
                return format_date(env, d, date_format=fmt)
            except Exception:
                pass
        if hasattr(d, "strftime"):
            return d.strftime(fmt or "%Y-%m-%d")
        return str(d)

    def _format_datetime(dt: Any, fmt: Optional[str] = None) -> str:
        if not dt:
            return ""
        if env:
            try:
                from odoo.tools import format_datetime
                return format_datetime(env, dt, dt_format=fmt)
            except Exception:
                pass
        if hasattr(dt, "strftime"):
            return dt.strftime(fmt or "%Y-%m-%d %H:%M:%S")
        return str(dt)

    def _format_amount(amt: Any, curr: Any = None) -> str:
        if amt is None:
            return ""
        currency = curr or getattr(record, "currency_id", None)
        if env and currency:
            try:
                from odoo.tools import format_amount
                return format_amount(env, amt, currency)
            except Exception:
                pass
        try:
            return f"{float(amt):,.2f}"
        except Exception:
            return str(amt)

    ctx: Dict[str, Any] = {
        "record": record,
        "records": records if records is not None else record,
        "fields": record,  # Alias allowing ${fields.partner_id.name}
        "company": company,
        "env": env,
        "user": user,
        "datetime": safe_datetime,
        "date": getattr(safe_datetime, "date", datetime.date),
        "time": safe_time,
        "Decimal": Decimal,
        "format_date": _format_date,
        "format_datetime": _format_datetime,
        "format_amount": _format_amount,
        "html2plaintext": normalize_html,
        "to_cell_value": to_cell_value,
        "resolve_path": resolve_path,
    }

    if isinstance(record, dict):
        ctx.update(record)

    # Evaluate custom variables and tables according to template configuration mode
    if template and getattr(template, "config_mode", None) == "code" and hasattr(template, "_execute_python_request"):
        try:
            py_res = template._execute_python_request(record=record, records=records)
            if py_res.get("variables"):
                ctx.update(py_res["variables"])
            if py_res.get("tables"):
                ctx["_python_tables"] = py_res["tables"]
        except Exception as e:
            _logger.warning("Error executing template python script: %s", e)
            if "_python_tables" not in ctx:
                ctx["_python_tables"] = {}
    elif template and hasattr(template, "variable_ids"):
        for var in template.variable_ids.sorted(key=lambda v: (v.sequence, v.id)):
            if var.name and var.code:
                try:
                    ctx[var.name] = evaluate_expression(var.code, ctx, strict=True)
                except Exception as e:
                    _logger.warning("Error evaluating variable '%s': %s", var.name, e)
                    ctx[var.name] = ""

    if extra:
        ctx.update(extra)

    return ctx


def evaluate_expression(
    expr: str,
    context: Dict[str, Any],
    strict: bool = False,
    cell_ref: Optional[str] = None,
) -> Any:
    """
    Evaluates a Python expression string within the given sandbox context.

    Args:
        expr: Expression string
        context: Context dictionary
        strict: If True, raise exception on errors; if False, log and return empty string
        cell_ref: Optional cell coordinate for informative error messages

    Returns:
        Evaluated value or fallback empty string
    """
    expr_str = expr.strip()
    if not expr_str:
        return ""

    # Fast-path resolution for common path prefixes
    if expr_str.startswith("fields."):
        return resolve_path(context.get("record"), expr_str[7:])
    if expr_str.startswith("company."):
        return resolve_path(context.get("company"), expr_str[8:])
    if expr_str in context:
        return context[expr_str]

    try:
        if safe_eval is not None:
            return safe_eval(expr_str, context, mode="eval")
        # Standalone pure-Python fallback evaluation
        safe_builtins = {
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "round": round,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "range": range,
        }
        eval_globals = {"__builtins__": safe_builtins}
        return eval(expr_str, eval_globals, context)
    except Exception as e:
        ref_info = f" at cell {cell_ref}" if cell_ref else ""
        if strict:
            raise RuntimeError(f"Failed to evaluate expression '${{{expr_str}}}'{ref_info}: {e}") from e
        _logger.warning("Template evaluation warning for '${%s}'%s: %s", expr_str, ref_info, e)
        return ""


def evaluate_expr(
    expr: str,
    context: Dict[str, Any],
    strict: bool = False,
    cell_ref: Optional[str] = None,
) -> Any:
    """Alias for evaluate_expression to match interface specification."""
    return evaluate_expression(expr, context, strict=strict, cell_ref=cell_ref)
