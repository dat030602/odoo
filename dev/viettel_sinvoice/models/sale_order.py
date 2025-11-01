# -*- coding: utf-8 -*-

from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    invoice_number = fields.Char(compute='_compute_invoice_number', string='Invoice Number', store=True, copy=False)

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.partner_invoice_id.is_company:
            res['partner_vat_id'] = self.partner_invoice_id.id
        else:
            res['partner_contact_id'] = self.partner_id.id
        return res

    @api.depends('invoice_ids', 'order_line.invoice_lines.move_id.state', 'order_line.invoice_lines.move_id.viettel_sinvoice_ids', 'order_line.invoice_lines.move_id.viettel_sinvoice_ids.state')
    def _compute_invoice_number(self):
        for order in self:
            invoices = order.order_line.invoice_lines.move_id.filtered(lambda m: m.state == 'posted')
            sinvoice_number = ' - '.join([inv.sinvoice_ref for inv in invoices if inv.sinvoice_ref])
            order.invoice_number = order.invoice_number and order.invoice_number + ' - ' + sinvoice_number or sinvoice_number or False

