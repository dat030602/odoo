"""
Connector Code Mixin
====================
Abstract mixin providing safe Python code execution for connector signatures
and request preparation. Uses odoo.tools.safe_eval for sandboxed execution.
"""

import logging
import datetime
import dateutil
import json

from odoo import models, fields, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ConnectorCodeMixin(models.AbstractModel):
    """Mixin that provides safe Python code execution capabilities.

    This mixin is used by connector.model.signature (for custom discovery logic)
    and connector.endpoint (for custom request preparation). It allows developers
    to write Python code that runs in a sandboxed environment using safe_eval.

    Available variables in the eval context:
        - env: The Odoo environment
        - record: The active record (from context)
        - records: The active records (from context)
        - context: The current context dict
        - log: A logging function
        - datetime, dateutil, json: Standard library modules
        - result: Must be assigned by the code (required output variable)
    """

    _name = "connector.code.mixin"
    _description = "Mixin for safe Python code execution in connectors"

    code = fields.Text(
        string="Python Code",
        groups="connector_base.group_connector_developer",
        help=(
            "Python code to execute. Available variables: env, record, records, "
            "context, log(msg), datetime, dateutil, json.\n"
            "Code MUST assign the variable `result` at the end."
        ),
    )

    def _get_eval_context(self, extra_context=None):
        """Build the evaluation context for safe_eval execution.

        :param extra_context: Additional variables to include in the context.
        :return: A dictionary containing all available variables for code execution.
        """
        self.ensure_one()
        ctx = {
            "env": self.env,
            "record": self.env.context.get("active_record"),
            "records": self.env.context.get("active_records"),
            "context": dict(self.env.context),
            "log": lambda msg: _logger.info(
                "[connector.code][%s#%s] %s", self._name, self.id, msg
            ),
            "datetime": datetime,
            "dateutil": dateutil,
            "json": json,
            "result": None,
        }
        if extra_context:
            ctx.update(extra_context)
        return ctx

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
            safe_eval(self.code, eval_context, mode="exec", nocopy=True)
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
            self.env["connector.code.execution.log"].sudo().create(log_vals)
