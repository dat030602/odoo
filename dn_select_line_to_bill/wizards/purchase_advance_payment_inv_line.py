from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PurchaseAdvancePaymentInvLine(models.TransientModel):
    _name = 'purchase.advance.payment.inv.line'
    _description = 'Custom Line Details'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('purchase.advance.payment.inv')
    is_select = fields.Boolean(string="Select", default=True)
    sequence = fields.Integer(string="Sequence", related='purchase_line_id.sequence', readonly=True, store=True)
    purchase_line_id = fields.Many2one('purchase.order.line', string="PO line", required=True)
    product_id = fields.Many2one(related='purchase_line_id.product_id', string="Product", readonly=True)
    max_qty = fields.Float(related='purchase_line_id.qty_to_invoice', string="Max Qty", readonly=True)
    qty_to_invoice = fields.Float(string="Quantity", required=True, digits='Product Unit', default=0.0)
    price_unit = fields.Float(related='purchase_line_id.price_unit', string="Unit Price", readonly=True)
    price_subtotal = fields.Float(string="Subtotal", readonly=True)
    price_total = fields.Float(string="Total", readonly=True)
    tax_ids = fields.Many2many(related='purchase_line_id.tax_ids', string="Taxes", readonly=True) # purchase uses taxes_id
    price_tax = fields.Float(string="Tax", readonly=True)
    currency_id = fields.Many2one(related='purchase_line_id.currency_id', string="Currency", readonly=True)

    @api.onchange('qty_to_invoice', 'price_unit', 'tax_ids')
    def _onchange_price_total(self):
        for rec in self:
            taxes = rec.tax_ids.compute_all(
                rec.price_unit, rec.purchase_line_id.currency_id, rec.qty_to_invoice, 
                product=rec.product_id, partner=rec.purchase_line_id.partner_id
            )
            rec.price_subtotal = taxes['total_excluded']
            rec.price_total = taxes['total_included']
            rec.price_tax = taxes['total_included'] - taxes['total_excluded']

    @api.constrains('qty_to_invoice', 'max_qty')
    def _check_qty_to_invoice(self):
        for rec in self:
            if rec.qty_to_invoice <= 0:
                raise ValidationError(_("Quantity to invoice must be greater than 0."))
            if round(rec.qty_to_invoice, 3) > round(rec.max_qty, 3):
                raise ValidationError(
                    _("Product %s: Quantity to invoice (%s) cannot be greater than the remaining quantity available for invoicing (%s).") % 
                    (rec.product_id.name, rec.qty_to_invoice, rec.max_qty)
                )
