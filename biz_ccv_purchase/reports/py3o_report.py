# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, tools


class Py3oReport(models.TransientModel):
    _inherit = "py3o.report"

    def _get_parser_context(self, model_instance, data):
        context = super(Py3oReport, self)._get_parser_context(model_instance, data)
        if model_instance._name == "purchase.order":
            context.update(model_instance.get_custom_py3o_context())
        return context
