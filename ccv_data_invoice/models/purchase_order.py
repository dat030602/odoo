from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import unidecode
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    supplier_invoice_ids = fields.Many2many('invoice.data', string='Hóa đơn nhà cung cấp', compute='_compute_supplier_invoices', store=True)

    @api.depends('invoice_ids.invoice_data_ids')
    def _compute_supplier_invoices(self):
        for order in self:
            order.supplier_invoice_ids = order.invoice_ids.invoice_data_ids

    def action_view_supplier_invoices(self, invs):
        self.ensure_one()
        if not invs:
            invs = self.supplier_invoice_ids
        action = self.env.ref('ccv_data_invoice.action_invoice_data').sudo().read()[0]
        if len(invs) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = invs.id
        else:
            action['domain'] = [('id', 'in', invs.ids)]
        return action

    def action_open_supplier_invoice_wizard(self):
        self.ensure_one()
        return {
            'name': _('Chọn hóa đơn điện tử'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.invoice.data.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
            },
        }
