import ast
import json
import logging
import re
from datetime import datetime

import xlsxwriter
from bs4 import BeautifulSoup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


def evaluate_expression(record, expression, localdict=None):
    """
    Expression Engine:
    Safely evaluates pythonic dot-notation strings and expressions against Odoo records.
    Example expressions: 
        - "partner_id.name" -> returns the partner's name.
        - "amount_total * 1.1" -> returns calculated VAT-inclusive total.
        - "len(line_ids)" -> returns child lines count.
    """
    if not expression or not record:
        return None

    # Default execution context with the current record represented as 'object' or 'rec'
    eval_context = {
        'record': record,
        'rec': record,
        'self': record,
        'datetime': datetime,
        'json': json,
        're': re,
    }
    if localdict:
        eval_context.update(localdict)

    # Clean the expression for dot-notation paths (e.g. 'partner_id.name' becomes 'record.partner_id.name')
    # If the expression doesn't contain python operators, treat it as a direct path
    is_simple_path = re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.]*$', expression.strip())

    if is_simple_path:
        expr_to_eval = f"record.{expression.strip()}"
    else:
        expr_to_eval = expression

    try:
        # Use safe_eval to get the evaluation outcome
        return safe_eval(expr_to_eval, eval_context)
    except Exception as e:
        _logger.warning("Expression evaluation failed for '%s' on record %s: %s", expression, record, e)
        return None


def compute_group_aggregates(data_records, group_by_field, aggregate_configs):
    """
    Group Builder & Aggregate Library:
    Groups a list of dict data by a given key, and calculates aggregates 
    (sum, avg, count, max, min, distinct_count).

    aggregate_configs format:
        [{"field": "amount", "operator": "sum"}, {"field": "id", "operator": "count"}]
    """
    grouped_data = {}

    for record in data_records:
        group_val = record.get(group_by_field) or "Undefined"
        if group_val not in grouped_data:
            grouped_data[group_val] = []
        grouped_data[group_val].append(record)

    results = []
    for group_name, records in grouped_data.items():
        summary = {
            "group_key": group_by_field,
            "group_value": group_name,
            "row_count": len(records),
            "aggregates": {}
        }

        for config in aggregate_configs:
            field = config.get("field")
            operator = config.get("operator", "sum")
            values = [r.get(field) for r in records if r.get(field) is not None]

            if not values:
                summary["aggregates"][f"{field}_{operator}"] = 0
                continue

            if operator == "sum":
                summary["aggregates"][f"{field}_sum"] = sum(values)
            elif operator == "avg":
                summary["aggregates"][f"{field}_avg"] = sum(values) / len(values)
            elif operator == "count":
                summary["aggregates"][f"{field}_count"] = len(values)
            elif operator == "distinct_count":
                summary["aggregates"][f"{field}_distinct_count"] = len(set(values))
            elif operator == "max":
                summary["aggregates"][f"{field}_max"] = max(values)
            elif operator == "min":
                summary["aggregates"][f"{field}_min"] = min(values)

        results.append(summary)

    return results

def format_workbook(workbook, font_size, font_name="Times New Roman", **kwargs):
    """
    Creates a flexible Excel format using xlsxwriter.
    """
    fmt = workbook.add_format()

    # Basic defaults
    fmt.set_font_name(font_name)
    fmt.set_font_size(font_size)
    fmt.set_align('vcenter')

    # Dynamically call xlsxwriter format configuration methods
    for key, value in kwargs.items():
        method_name = f"set_{key}"
        if hasattr(fmt, method_name):
            getattr(fmt, method_name)(value)
        else:
            raise ValueError(f"Method {method_name} does not exist on xlsxwriter format.")

    return fmt


def safe_dict(data_dict, key):
    """
    Safely parses configuration string elements into Python datatypes.
    """
    raw_value = data_dict.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        if not raw_value.strip():
            return raw_value
        try:
            evaluated_value = ast.literal_eval(raw_value)
            if isinstance(evaluated_value, str) and evaluated_value == raw_value:
                pass
            else:
                return evaluated_value
        except (ValueError, SyntaxError):
            pass
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            pass
        return raw_value
    return raw_value


def remove_prefix_from_string(input_string: str):
    """
    Trims standard prefixes from formatted code-strings (e.g. "US - United States" -> "United States")
    """
    if not input_string:
        return ""

    if ' - ' in input_string:
        separator_index = input_string.find(' - ')
        return input_string[separator_index + len(' - '):].strip()
    return input_string.strip()


def safe_value(value):
    """
    Safely converts a value to a string, handling None and other types.
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return str(value)
