# -*- coding: utf-8 -*-
import ast
import inspect
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from ..services import helper


class ExcelReportFunction(models.Model):
    _name = "excel.report.function"
    _description = "Excel Report Function"

    name = fields.Char(string="Name", required=True)
    code = fields.Text(
        string="Code", 
        required=True,
        help="Write custom scripts. Expose output via variable 'result'."
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)

    @api.model
    def _register_hook(self):
        res = super()._register_hook()
        self._sync_builtin_functions()
        return res

    @api.model
    def _sync_builtin_functions(self):
        existed = set(self.search([]).mapped("name"))

        vals = []

        for name, func in inspect.getmembers(helper, inspect.isfunction):
            if name.startswith("_"):
                continue

            if name in existed:
                continue

            signature = str(inspect.signature(func))
            doc = inspect.getdoc(func) or "No description."

            description = (
                f"Signature:\n"
                f"{name}{signature}\n\n"
                f"Description:\n"
                f"{doc}"
            )

            vals.append({
                "name": name,
                "code": inspect.getsource(func),
                "description": description,
            })

        if vals:
            self.create(vals)

    def execute(self, localdict=None):
        self.ensure_one()
        if not self.code:
            return None

        eval_context = {
            'datetime': datetime,
            'ast': ast,
            'json': json,
            're': re,
            'BeautifulSoup': BeautifulSoup,
            'UserError': UserError,
            'result': None,
        }

        for attr_name, attr_value in inspect.getmembers(helper):
            if inspect.isfunction(attr_value) and not attr_name.startswith('_'):
                if attr_name == 'evaluate_expression':
                    eval_context[attr_name] = lambda record, expr, l_dict=None: attr_value(
                        record, expr, localdict=l_dict, safe_eval_func=safe_eval
                    )
                else:
                    eval_context[attr_name] = attr_value

        if localdict:
            eval_context.update(localdict)

        safe_eval(self.code.strip(), eval_context, mode="exec", nocopy=True)
        return eval_context.get('result')
