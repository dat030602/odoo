"""
Connector Code Mixin
====================
Abstract mixin providing safe Python code execution for connector signatures
and request preparation. Uses odoo.tools.safe_eval for sandboxed execution.
"""

import ast
import base64
import datetime
import dateutil
import hashlib
import hmac
import http.client
import io
import json
import logging
import math
import random
import re
import sys
import types
import urllib
import xmlrpc.client

from odoo import models, fields, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.safe_eval import safe_eval, wrap_module

_logger = logging.getLogger(__name__)

DISALLOWED_MODULES = frozenset({
    "os", "subprocess", "sys", "shutil", "builtins", "__builtin__",
    "importlib", "socket", "pty", "posix", "ctypes", "pickle", "multiprocessing",
})


class _AssertTransformer(ast.NodeTransformer):
    """Rewrite AST Assert nodes into if-not-raise statements
    to support assert in Python 3.12 without requiring LOAD_ASSERTION_ERROR in _SAFE_OPCODES.
    """

    def visit_Assert(self, node):
        msg = [node.msg] if node.msg else []
        new_node = ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=node.test),
            body=[
                ast.Raise(
                    exc=ast.Call(
                        func=ast.Name(id="AssertionError", ctx=ast.Load()),
                        args=msg,
                        keywords=[],
                    ),
                    cause=None,
                )
            ],
            orelse=[],
        )
        return ast.copy_location(new_node, node)


def _sanitize_code(code_str):
    """Transforms code string so statements like assert work with Odoo safe_eval."""
    if not code_str or not isinstance(code_str, str):
        return code_str or ""
    try:
        tree = ast.parse(code_str)
        tree = _AssertTransformer().visit(tree)
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
    except Exception:
        return code_str


def _dynamic_import(mod):
    """Dynamic module importer for safe_eval environments with security sandbox enforcement."""
    if not mod or not isinstance(mod, str):
        raise AccessError(_("Invalid module name."))
    root_pkg = mod.split(".")[0].strip()
    if root_pkg in DISALLOWED_MODULES:
        if mod == "sys":
            # Restricted read-only sys attributes (e.g. version_info) for compatibility
            # while strictly preventing sys.modules sandbox breakout
            return wrap_module(sys, ["version_info", "version", "hexversion", "byteorder"])
        raise AccessError(_("Importing '%s' is prohibited.", mod))

    if mod in sys.modules:
        target = sys.modules[mod]
    else:
        __import__(mod)
        target = sys.modules[mod]

    attrs = [
        a for a in dir(target)
        if not a.startswith("_") and not isinstance(getattr(target, a, None), types.ModuleType)
    ]
    return wrap_module(target, attrs)


def _prepare_safe_eval_context(ctx):
    """Sanitizes context dict by wrapping any raw types.ModuleType with safe_eval.wrap_module."""
    res = {}
    for k, v in (ctx or {}).items():
        if isinstance(v, types.ModuleType):
            attrs = [
                a for a in dir(v)
                if not a.startswith("_") and not isinstance(getattr(v, a, None), types.ModuleType)
            ]
            res[k] = wrap_module(v, attrs)
        else:
            res[k] = v

    defaults = {
        "callable": callable,
        "RuntimeError": RuntimeError,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AttributeError": AttributeError,
        "ZeroDivisionError": ZeroDivisionError,
        "AssertionError": AssertionError,
        "_import": _dynamic_import,
        "_dynamic_import": _dynamic_import,
    }
    for k, v in defaults.items():
        if k not in res:
            res[k] = v
    return res


def _execute_safe_eval(code, eval_context, mode="exec"):
    """Safely executes code within sanitized context."""
    clean_code = _sanitize_code(code)
    clean_ctx = _prepare_safe_eval_context(eval_context)
    safe_eval(clean_code, clean_ctx, mode=mode)
    eval_context.update(clean_ctx)
    return eval_context.get("result")


class ConnectorCodeMixin(models.AbstractModel):
    """Mixin that provides safe Python code execution capabilities.

    This mixin is used by connector.model.signature (for custom discovery logic)
    and connector.outbound.endpoint (for custom request preparation). It allows developers
    to write Python code that runs in a sandboxed environment using safe_eval.
    """

    _name = "connector.code.mixin"
    _description = "Mixin for safe Python code execution in connectors"

    code = fields.Text(
        string="Python Code",
        groups="dn_connector_base.group_connector_developer",
        help=(
            "Python code to execute. Available variables: env, record, records, "
            "context, log(msg), datetime, dateutil, json, re, math, _import, _dynamic_import.\n"
            "Code MUST assign the variable `result` at the end."
        ),
    )

    def _get_eval_context(self, extra_context=None):
        """Build the evaluation context for safe_eval execution.

        :param extra_context: Additional variables to include in the context.
        :return: A dictionary containing all available variables for code execution.
        """
        ctx = {
            "env": self.env,
            "record": self.env.context.get("active_record", False),
            "records": self.env.context.get("active_records", False),
            "context": dict(self.env.context),
            "log": lambda msg: _logger.info(
                "[connector.code][%s] %s",
                getattr(self, "_name", "connector.code.mixin"),
                msg,
            ),
            "result": None,
            "_import": _dynamic_import,
            "_dynamic_import": _dynamic_import,
            "callable": callable,
            "RuntimeError": RuntimeError,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "ZeroDivisionError": ZeroDivisionError,
            "AssertionError": AssertionError,
            "re": re,
            "datetime": datetime,
            "dateutil": dateutil,
            "json": json,
            "math": math,
            "random": random,
            "io": io,
            "hashlib": hashlib,
            "hmac": hmac,
            "urllib": urllib,
            "ast": ast,
            "base64": base64,
            "xmlrpc": xmlrpc,
            "http": http.client,
            "user": self.env.user,
            "UserError": UserError,
            "ValidationError": ValidationError,
        }
        if extra_context:
            ctx.update(extra_context)
        return _prepare_safe_eval_context(ctx)

    def execute_code(self, extra_context=None, raise_on_error=True):
        """Execute the Python code stored in the `code` field using safe_eval.

        The code must assign a value to the `result` variable. Execution is
        logged to connector.code.execution.log for audit purposes.

        :param extra_context: Additional variables to pass into the eval context.
        :param raise_on_error: If True, raises ValidationError on execution failure.
        :return: The value assigned to `result` by the executed code.
        :raises ValidationError: If code is empty or execution fails (when raise_on_error=True).
        """
        self.ensure_one()
        if not self.code:
            raise ValidationError(_("No code defined for %s") % self.display_name)

        eval_context = self._get_eval_context(extra_context)
        log_vals = {
            "res_model": self._name,
            "res_id": self.id,
            "code_snapshot": self.code,
            "user_id": self.env.uid,
        }
        try:
            _execute_safe_eval(self.code, eval_context, mode="exec")
            result = eval_context.get("result")
            log_vals.update({
                "state": "success",
                "result_summary": str(result)[:2000],
            })
            return result
        except Exception as e:
            log_vals.update({
                "state": "error",
                "error_message": str(e),
            })
            _logger.exception(
                "Error executing code on %s#%s", self._name, self.id
            )
            if raise_on_error:
                raise ValidationError(
                    _("Error executing code:\n%s") % str(e)
                ) from e
            return None
        finally:
            self.env["connector.code.execution.log"].sudo().create(log_vals)  # sudo: audit logging of code execution
