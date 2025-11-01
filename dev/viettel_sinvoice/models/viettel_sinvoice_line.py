# -*- coding: utf-8 -*-

from datetime import date

import logging

from odoo import models, fields, api, _
# from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

_logger = logging.getLogger(__name__)

LINE_SELECTION = [
    ('1', 'Hàng hoá'),
    ('2', 'Ghi chú'),
    ('3', 'Chiết khấu'),
    ('4', 'Bảng kê'),
    ('5', 'Phí khác')
]

class ViettelSinvoiceData(models.Model):
    _name = "viettel.sinvoice.line"
    _description = "S-Invoice Line Items"

    @api.depends('price_unit', 'discount', 'sinvoice_line_tax_id', 'quantity',
                 'product_id', 'sinvoice_id.partner_vat_id', 'sinvoice_id.partner_id', 'sinvoice_id.currency_id',
                 'sinvoice_id.company_id', 'sinvoice_id.date_invoice', 'sinvoice_id.date')
    def _compute_price(self):
        for line in self:
            currency = line.sinvoice_id and line.sinvoice_id.currency_id
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            partner = line.sinvoice_id.partner_vat_id or line.sinvoice_id.partner_id
            taxes = line.sinvoice_line_tax_id.compute_all(price, currency, line.quantity, product=line.product_id, partner=partner)
            # Set Unit Price after discount
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'price_subtotal_signed': taxes['total_excluded'],
                'price_discount': (line.price_unit * line.quantity - taxes['total_excluded'])
            })
            if currency and currency != line.sinvoice_id.company_id.currency_id:
                rate_date = line.sinvoice_id._get_currency_rate_date()
                price_subtotal_signed = currency._convert(line.price_subtotal_signed,
                                                          line.sinvoice_id.company_id.currency_id,
                                                          line.company_id or self.env.user.company_id,
                                                          rate_date or fields.Date.today())
                line.price_subtotal_signed = price_subtotal_signed

    @api.model
    def _default_account(self):
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            return journal.default_account_id.id

    sinvoice_id = fields.Many2one('viettel.sinvoice', string='Sinvoice', ondelete='cascade', required=True, index=True,
                                  copy=False, readonly=True)
    state = fields.Selection(related='sinvoice_id.state', string='State', store=True)
    name = fields.Text(string='Description', readonly=False, store=True, required=True)
    origin = fields.Char(string='Source Document', help="Reference of the document that produced this invoice.")
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying the invoice.")

    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', ondelete='set null', index=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)],
                                 default=_default_account,
                                 help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Monetary(string='Total', store=True, readonly=True,
                                     compute='_compute_price', help="Total amount without taxes")
    price_total = fields.Monetary(string='Amount (with Taxes)', store=True, readonly=True, compute='_compute_price',
                                  help="Total amount with taxes")
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id', store=True,
                                            readonly=True, compute='_compute_price',
                                            help="Total amount in the currency of the company, negative for credit note.")
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_price', store=True)
    price_discount = fields.Monetary(string='Price Discount', compute='_compute_price', store=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    sinvoice_line_tax_id = fields.Many2one('account.tax', string='Taxes',
                                           domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                                                   ('active', '=', True)])

    edit_type = fields.Selection([('increase', 'Increase'), ('reduction', 'Reduction')],
                                 string='Edit Type', default=False, readonly=True)
    model = fields.Char(string="Model")
    reference_id = fields.Char(string="Reference")
    company_id = fields.Many2one('res.company', string='Company', related='sinvoice_id.company_id', store=True,
                                 readonly=True)
    partner_vat_id = fields.Many2one('res.partner', string='Legal S-invoice Customer',
                                     related='sinvoice_id.partner_vat_id', store=True,
                                     readonly=True)
    partner_id = fields.Many2one('res.partner', string='S-Invoice Contact', related='sinvoice_id.partner_id',
                                 store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='sinvoice_id.currency_id', store=True, readonly=False)
    company_currency_id = fields.Many2one('res.currency', related='sinvoice_id.company_currency_id', readonly=True)
    selection = fields.Selection(LINE_SELECTION, string='Type', default='1', required=True)
    display_type =  fields.Char(compute='_compute_display_type')
    org_line_id = fields.Many2one('viettel.sinvoice.line', 'Original S-Invoice Line', readonly=True)
    child_line_id = fields.One2many('viettel.sinvoice.line', 'org_line_id', string='Children Line')
    is_valid = fields.Boolean(compute='_compute_valid_line', store=True)
    invoiceIssuedDate = fields.Datetime(related='sinvoice_id.invoiceIssuedDate', string='Issued Date', store=True)

    def _compute_display_type(self):
        for line in self:
            if line.selection == '2':
                line.display_type = 'line_note'
            else:
                line.display_type = False

    @api.depends('sinvoice_id', 'sinvoice_id.state', 'state', 'child_line_id')
    def _compute_valid_line(self):
        for l in self:
            if l.state in ('draft', 'confirm', 'canceled', 'is_replaced', 'edit_info'):
                l.is_valid = False
            elif l.state in ('created', 'replace', 'edit_amount', 'is_edited_info', 'is_edited_amount'):
                l.is_valid = True

    @api.constrains('edit_type', 'org_line_id', 'sinvoice_id', 'price_unit', 'discount', 'selection', 'quantity', 'price_total')
    def _check_edit_type_not_null(self):
        for line in self:
            if float_compare(line.quantity, 0, 0) == -1:
                raise UserError('Số lượng sản phẩm phải là số dương !')
            if line.sinvoice_id.adjustmentInvoiceType == '1' and line.sinvoice_id.adjustmentType == '5':
                if not line.edit_type:
                    raise UserError('Loại điều chỉnh tăng giảm bắt buộc đối với Hoá đơn điều chỉnh tiền !')
                if not line.org_line_id:
                    raise UserError('Phải chọn dòng cần chỉnh sửa từ hoá đơn điện tử gốc !')
                if line.discount:
                    raise UserError('Hoá đơn chỉnh sửa không hỗ trợ chiết khấu !')
            else:
                if float_compare(line.price_total, 0, 0) == -1 and line.selection != '3':
                    raise UserError('Thành tiền phải là số dương đối với dòng sản phẩm là Hàng hoá'
                                    ' của Hoá đơn gốc và Hoá đơn thay thế %s!' % line.name)
            # Check and valid discount value between
            if float_compare(line.discount, 100, 0) == 1 or float_compare(line.discount, 0, 0) == -1:
                raise UserError('Chiết khấu phải lớn hơn 0 và nhỏ hơn 100 !')

            if line.selection == '3':
                if float_compare(line.price_unit, 0, 0) != -1:
                    raise UserError('Đơn giá sản phẩm là chiết khấu phải là số âm !')
                if float_compare(line.discount, 0, 0) != 0:
                    raise UserError('Dòng sản phẩm chiết khấu không hỗ trợ tiền chiết khấu !')
            # Check if the s-invoice is internal transfer
            if line.sinvoice_id.invoiceType.code == '03XKNB':
                if line.selection != '1':
                    raise UserError('Hoá đơn xuất kho - Kiêm vận chuyển nội bộ, sản phẩm phải là hàng hoá !')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.sinvoice_id:
            return

        partner_vat_id = self.sinvoice_id.partner_vat_id
        partner_id = self.sinvoice_id.partner_id
        partner = partner_vat_id or partner_id
        if not partner_vat_id and not partner_id:
            warning = {
                'title': _('Warning!'),
                'message': _('You must first select a partner !'),
            }
            return {'warning': warning}

        else:
            self_lang = self
            if partner.lang:
                self_lang = self.with_context(lang=partner.lang)

            company_id = self.company_id or self.env.user.company_id
            taxes = self.product_id.taxes_id.filtered(lambda r: r.company_id == company_id) \
                    or self.account_id.tax_ids or self.sinvoice_id.company_id.account_sale_tax_id
            tax = self.sinvoice_id.fiscal_position_id.map_tax(taxes)
            if tax:
                self.sinvoice_line_tax_id = tax[0] or False
            if self.sinvoice_id.invoiceType.code == '03XKNB':
                self.sinvoice_line_tax_id = False
            product = self_lang.product_id
            if product:
                self.name = product.name

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id

            self.price_unit = product.list_price

            if self.uom_id and self.uom_id.id != product.uom_id.id:
                self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)

            # if not self.sinvoice_id.adjustmentInvoiceType == '1' and not self.sinvoice_id.adjustmentType == '5' and \
            #         float_compare(self.price_unit, 0, 0) == -1 and self.selection != '3':
            #     raise UserError('Đơn giá phải là số dương đối với Hoá đơn gốc và Hoá đơn thay thế !')
