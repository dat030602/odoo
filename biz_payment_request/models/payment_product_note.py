from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PaymentProductNote(models.Model):
    _name = "payment.product.note"
    _description = "Payment Product Note"

    name = fields.Char("Mô tả")
    product_id = fields.Many2one("product.product", "Sản phẩm")
    fprice_unit = fields.Monetary("Đơn giá ngoại tệ", currency_field='currency_id')
    price_unit = fields.Monetary("Đơn giá vnd", compute="_compute_price_unit", store=True, readonly=False, currency_field='company_currency_id')
    quantity = fields.Float("Số lượng", default=1.0, digits='Product Unit of Measure')
    invoice_date = fields.Date("Ngày",default=fields.Date.today())
    invoice_name = fields.Char("Số hóa đơn")
    uom_id = fields.Many2one("uom.uom", string="Đơn vị tính")

    famount_untax = fields.Monetary("Giá chưa thuế ngoại tệ", compute="_compute_famount_untax", store=True, readonly=False, currency_field='currency_id')
    amount_untax = fields.Monetary("Giá chưa thuế vnd", compute="_compute_amount_untax", store=True, readonly=False, currency_field='company_currency_id')
    famount_tax = fields.Monetary("Tiền thuế ngoại tệ", compute="_compute_famount_tax", store=True, readonly=False, currency_field='currency_id')
    amount_tax = fields.Monetary("Tiền thuế vnd", compute="_compute_amount_tax", store=True, readonly=False, currency_field='company_currency_id')
    amount_total = fields.Monetary("Thành tiền vnd", compute="_compute_amount_total", store=True, readonly=False, currency_field='company_currency_id')
    tax_id = fields.Many2one("account.tax", "Thuế")

    payment_request_id = fields.Many2one('payment.request')
    alpha_internal_account_id = fields.Many2one('alpha.internal.account')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.context.get('force_currency_id') or self.env.company.currency_id.id)
    company_currency_id = fields.Many2one('res.currency', string='Tiền tệ Cty', default=lambda self: self.env.context.get('force_company_currency_id') or self.env.company.currency_id.id)

    fcurrency_rate = fields.Float(string="Tỷ giá", default=lambda self: self.env.context.get('force_fcurrency_rate') or 1.0)
    fcurrent_amount = fields.Monetary(string="Thành tiền ngoại tệ", compute="_compute_fcurrent_amount", store=True, readonly=False, currency_field='currency_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.uom_id = rec.product_id.uom_id

    @api.depends('fprice_unit', 'fcurrency_rate')
    def _compute_price_unit(self):
        for rec in self.sudo():
            rec.price_unit = rec.fprice_unit * (rec.fcurrency_rate or 1.0)

    @api.depends('fprice_unit', 'quantity')
    def _compute_famount_untax(self):
        for rec in self.sudo():
            rec.famount_untax = rec.fprice_unit * rec.quantity

    @api.depends('famount_untax', 'fcurrency_rate')
    def _compute_amount_untax(self):
        for rec in self.sudo():
            rec.amount_untax = rec.famount_untax * (rec.fcurrency_rate or 1.0)

    @api.depends('fprice_unit', 'quantity', 'tax_id')
    def _compute_famount_tax(self):
        for rec in self.sudo():
            if rec.tax_id:
                taxes = rec.tax_id.compute_all(rec.fprice_unit, rec.currency_id, rec.quantity, product=rec.product_id)
                rec.famount_tax = taxes['total_included'] - taxes['total_excluded']
            else:
                rec.famount_tax = 0.0

    @api.depends('famount_tax', 'fcurrency_rate')
    def _compute_amount_tax(self):
        for rec in self.sudo():
            rec.amount_tax = rec.famount_tax * (rec.fcurrency_rate or 1.0)

    @api.depends('quantity', 'fprice_unit', 'famount_tax')
    def _compute_fcurrent_amount(self):
        for rec in self.sudo():
            rec.fcurrent_amount = rec.quantity * rec.fprice_unit + rec.famount_tax

    @api.depends('quantity', 'price_unit', 'amount_tax')
    def _compute_amount_total(self):
        for rec in self.sudo():
            rec.amount_total = rec.quantity * rec.price_unit + rec.amount_tax

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax'].sudo()._convert_to_tax_base_line_dict(
            self,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.fprice_unit,
            quantity=self.quantity,
            price_subtotal=self.famount_untax,
        )
