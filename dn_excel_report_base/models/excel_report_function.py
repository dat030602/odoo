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
