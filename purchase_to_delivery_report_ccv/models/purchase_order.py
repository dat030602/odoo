# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    export_delivery_report_count = fields.Integer(compute='_compute_export_delivery_report_count')

    def _compute_export_delivery_report_count(self):
        for order in self:
            order.export_delivery_report_count = self.env['export.delivery.report.ccv'].search_count([('purchase_id', '=', order.id)])

    def action_view_export_delivery_report(self):
        self.ensure_one()
        return {
            'name': _('Thông tin trình duyệt'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'export.delivery.report.ccv',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'default_purchase_id': self.id},
        }

    def action_open_export_delivery_report_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export Delivery Orders Report'),
            'res_model': 'export.delivery.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_origin': self.name,
            },
        }
