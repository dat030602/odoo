from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleAdvancePaymentInvLine(models.TransientModel):
    _name = 'sale.advance.payment.inv.line'
    _description = 'Custom Line Details'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('sale.advance.payment.inv')
    is_select = fields.Boolean(string="Select", default=True)
    sequence = fields.Integer(string="Sequence", related='sale_line_id.sequence', readonly=True, store=True)
    sale_line_id = fields.Many2one('sale.order.line', string="SO line", required=True)
    product_id = fields.Many2one(related='sale_line_id.product_id', string="Product", readonly=True)
    max_qty = fields.Float(related='sale_line_id.qty_to_invoice', string="Max Qty", readonly=True, digits="Product Unit")
    qty_to_invoice = fields.Float(string="Quantity", required=True, digits="Product Unit")
    price_unit = fields.Float(related='sale_line_id.price_unit', string="Unit Price", readonly=True)
    price_subtotal = fields.Monetary(string="Subtotal", readonly=True)
    price_total = fields.Monetary(string="Total", readonly=True)
    tax_ids = fields.Many2many(related='sale_line_id.tax_ids', string="Taxes", readonly=True)
    price_tax = fields.Monetary(string="Tax", readonly=True)
    currency_id = fields.Many2one(related='sale_line_id.order_id.currency_id', string="Currency", readonly=True)

    @api.onchange('qty_to_invoice', 'price_unit', 'tax_ids')
    def _onchange_price_total(self):
        for rec in self:
            taxes = rec.tax_ids.compute_all(rec.price_unit, rec.sale_line_id.order_id.currency_id, rec.qty_to_invoice, product=rec.product_id, partner=rec.sale_line_id.order_id.partner_shipping_id)
            rec.price_subtotal = taxes['total_excluded']
            rec.price_total = taxes['total_included']
            rec.price_tax = taxes['total_included'] - taxes['total_excluded']

    @api.constrains('qty_to_invoice', 'max_qty')
    def _check_qty_to_invoice(self):
        for rec in self:
            if rec.qty_to_invoice <= 0:
                raise ValidationError(_("Quantity to invoice must be greater than 0."))
            if rec.qty_to_invoice > rec.max_qty:
                raise ValidationError(
                    _("Product %s: Quantity to invoice (%s) cannot be greater than the remaining quantity available for invoicing (%s).") % 
                    (rec.product_id.name, rec.qty_to_invoice, rec.max_qty)
                )
