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
from markupsafe import Markup

_logger = logging.getLogger(__name__)


def evaluate_expression(record, expression, localdict=None):
    """
    Expression Engine:
    Safely evaluates pythonic dot-notation strings and expressions against Odoo records.
    Example expressions: 
        - "partner_id.name" -> returns the partner's name.
        - "amount_total * 1.1" -> returns calculated VAT-inclusive total.
        - "len(line_ids)" -> returns child lines count.

    Args:
        record (odoo.models.Model): The Odoo record to evaluate against.
        expression (str): The dot-notation string or pythonic expression to evaluate.
        localdict (dict, optional): Additional local variables to include in the evaluation context. Defaults to None.
    
    Returns:
        The result of the evaluated expression, or None if evaluation fails.
    
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


def safe_dict(data_dict, key):
    """
    Safely parses configuration string elements into Python datatypes.

    Args:
        data_dict (dict): The dictionary containing the data.
        key (str): The key to look up in the dictionary.
    Returns:
        The parsed value, which can be a string, int, float, bool, list, dict, or None.
    
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
    Removes the prefix from a string if it contains ' - '.
    Example: "Prefix - Actual Value" -> "Actual Value"

    Args:
        input_string (str): The string to process.
    
    Returns:
        str: The string without the prefix.
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

    Args:
        value: Any python object.

    Returns:
        String representation.
    """

    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return str(value)
