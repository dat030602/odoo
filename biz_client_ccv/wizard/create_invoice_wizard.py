import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class CreateInvoiceWizard(models.TransientModel):
    _name = 'create.invoice.wizard'
    _description = 'Create Invoice Wizard'

    order_reference_id = fields.Many2one('sale.order','Sale Order',domain=[('state','in',['sale','done'])])
    purchase_reference_id = fields.Many2one('purchase.order','Purchase Order',domain=[('state','in',['purchase','done'])])

    def create_invoice(self):
        if self.order_reference_id:
            return self.action_create_invoice_sale()
        if self.purchase_reference_id:
            return self.action_create_invoice_purchase()

    def action_create_invoice_sale(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_view_sale_advance_payment_inv")
        so_ids = self.order_reference_id.ids
        action['context'] = {
            'active_id': so_ids[0] if len(so_ids) == 1 else False,
            'active_ids': so_ids
        }
        return action

    def action_create_invoice_purchase(self):
        return self.purchase_reference_id.action_create_invoice()