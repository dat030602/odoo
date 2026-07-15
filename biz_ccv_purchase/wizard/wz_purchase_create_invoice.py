from odoo import api, fields, models, tools, _
from datetime import datetime,timedelta

from odoo.exceptions import UserError, ValidationError

class WzPurchaseInvoice(models.TransientModel):
	_name = 'wz.purchase.invoive'
	_description = 'Created invoive from purchase'

	purchase_id = fields.Many2one("purchase.order")
	order_line = fields.One2many('wz.purchase.invoive.line','wizard_id', string="Selects")

	def action_confirm(self):
		lines = self.order_line.filtered(lambda x: x.is_selected)
		if not lines:
			raise ValidationError(_("Please select product to invoice"))

		print("~~lines", lines, lines.mapped("purchase_line_id"))
		return self.purchase_id.action_done_create_invoice_ccv(lines.mapped("purchase_line_id"))

class WzPurchaseInvoiceLine(models.TransientModel):
	_name = 'wz.purchase.invoive.line'
	_description = 'Created invoive from purchase'

	wizard_id = fields.Many2one("wz.purchase.invoive",  ondelete="cascade")
	purchase_line_id = fields.Many2one("purchase.order.line")
	is_selected = fields.Boolean('Selected')

	date_planned = fields.Datetime('Date planned', related='purchase_line_id.date_planned')
	currency_id = fields.Many2one("res.currency", 'Currency', related='purchase_line_id.currency_id')
	product_id = fields.Many2one("product.product", 'Product', related='purchase_line_id.product_id')
	name = fields.Text("Description", related='purchase_line_id.name')
	analytic_distribution = fields.Json('Analytic', related='purchase_line_id.analytic_distribution')
	product_qty = fields.Float("Quantity", related='purchase_line_id.product_qty')
	qty_received = fields.Float("Received", related='purchase_line_id.qty_received')
	qty_invoiced = fields.Float("Bill", related='purchase_line_id.qty_invoiced')
	product_uom = fields.Many2one("uom.uom",'UoM', related='purchase_line_id.product_uom')
	price_unit = fields.Float("Price unit", related='purchase_line_id.price_unit')
	taxes_id = fields.Many2many("account.tax", string='Taxes', related='purchase_line_id.taxes_id')
	price_subtotal = fields.Monetary("Subtotal", related='purchase_line_id.price_subtotal')
	analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
