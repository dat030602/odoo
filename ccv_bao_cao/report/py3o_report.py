# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, tools


class Py3oReport(models.TransientModel):
    _inherit = "py3o.report"

    def _get_parser_context(self, model_instance, data):
        context = super(Py3oReport, self)._get_parser_context(model_instance, data)
        if self.ir_actions_report_id and self.ir_actions_report_id.report_name in ['py3o_saleorder_2025', 'py3o_saleorder_2025_pdf', 'py3o_saleorder_2026'] and model_instance and model_instance._name == 'sale.order':
            context.update(model_instance.get_report_saleorder_2025_docx_context())
        if self.ir_actions_report_id and self.ir_actions_report_id.report_name in ['py3o_purchaseorder_2025', 'py3o_purchaseorder_2025_pdf'] and model_instance and model_instance._name == 'purchase.order':
            context.update(model_instance.get_report_purchaseorder_2025_docx_context())
        if self.ir_actions_report_id and self.ir_actions_report_id.report_name in ['py3o_quotation_sale_2025'] and model_instance and model_instance._name == 'quotation.report.wizard':
            context.update(model_instance.get_report_docx_context())
        return context
