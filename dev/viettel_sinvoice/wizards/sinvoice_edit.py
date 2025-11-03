# -*- coding: utf-8 -*-
import uuid
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

EDIT_TYPE = [
    ('info', 'Điều chỉnh thông tin'),
    ('amount', 'Điều chỉnh tiền'),
    ('replace', 'Lập hóa đơn thay thế'),
]
LINE_SELECTION = [
    ('1', 'Hàng hoá'),
    ('2', 'Ghi chú'),
    ('3', 'Chiết khấu'),
    ('4', 'Bảng kê'),
    ('5', 'Phí khác')
]


class ViettelSinvoiceEdit(models.TransientModel):
    _name = "viettel.sinvoice.edit"
    _description = "Sinvoice edit"

    sinvoice_edit_type = fields.Selection(EDIT_TYPE, 'Type', default='info', required=True)
    sinvoice_id = fields.Many2one('viettel.sinvoice', 'Sinvoice')
    partner_id = fields.Many2one('res.partner', string='S-Invoice Contact')
    partner_vat_id = fields.Many2one('res.partner', string='Legal S-Invoice Customer',
                                     domain="[('is_company','=',True)]")
    additionalReferenceDesc = fields.Char('Additional Reference Description')
    additionalReferenceDate = fields.Date('Additional Reference Date')
    invoiceIssuedDate = fields.Datetime('Invoice Issued Date', required=True)  # Thời gian phát hành
    buyerPhoneNumber = fields.Char('Customer Phone')
    customer_name = fields.Char('Contact Name')
    legal_customer_name = fields.Char('S-Invoice Customer Name')
    customer_code = fields.Char('Customer Code')
    customer_vat = fields.Char('VAT')
    customer_email = fields.Char('Customer Emails')
    customer_address = fields.Char('VAT Address')

    new_buyerPhoneNumber = fields.Char('New Customer Phone', compute='_compute_new_customer_info', store=True)
    new_customer_name = fields.Char('New Contact Name', compute='_compute_new_customer_info', store=True)
    new_customer_code = fields.Char('New Customer Code', compute='_compute_new_customer_info', store=True)
    new_customer_vat = fields.Char('New VAT', compute='_compute_new_customer_info', store=True)
    new_customer_email = fields.Char('New Customer Emails', compute='_compute_new_customer_info', store=True)
    new_legal_customer_name = fields.Char('New S-Invoice Customer Name', compute='_compute_new_customer_info', store=True)
    new_customer_address = fields.Char('New VAT Address', compute='_compute_new_customer_info', store=True)

    viettel_sinvoice_template_id = fields.Many2one('viettel.sinvoice.template', string="Config Template")
    branch_id = fields.Many2one('company.branch', related='viettel_sinvoice_template_id.branch_id', string='Branch')
    supplierTaxCode = fields.Char(related='viettel_sinvoice_template_id.vat')
    vsi_template = fields.Char(related='viettel_sinvoice_template_id.template_code', string='Mẫu Hóa Đơn')
    series = fields.Char(related='viettel_sinvoice_template_id.series', string='Series')
    originalInvoiceId = fields.Char("Original Invoice Id")
    company_id = fields.Many2one('res.company', string='Company')
    sinvoice_edit_line = fields.One2many('viettel.sinvoice.line.edit', 'sinvoice_edit_id', string='S-Invoice Lines', )
    journal_id = fields.Many2one('account.journal', string='Journal')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')

    currency_id = fields.Many2one('res.currency', related='sinvoice_id.currency_id', string='Currency', required=True,
                                  readonly=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', readonly=True, compute='_compute_amount', copy=False,
                                     currency_field='currency_id')
    amount_tax = fields.Monetary(string='Tax', readonly=True, compute='_compute_amount', copy=False)
    amount_total = fields.Monetary(string='Total', readonly=True, compute='_compute_amount', copy=False)

    @api.depends('sinvoice_edit_line.price_subtotal', 'sinvoice_edit_line.price_tax')
    def _compute_amount(self):
        self.amount_untaxed = round(sum(line.price_subtotal for line in self.sinvoice_edit_line), 0)
        self.amount_tax = round(sum(line.price_tax for line in self.sinvoice_edit_line), 0)
        self.amount_total = self.amount_untaxed + self.amount_tax

    @api.constrains('sinvoice_edit_line', 'sinvoice_edit_type', 'sinvoice_id', 'partner_vat_id', 'partner_id',
                    'new_customer_vat', 'customer_address')
    def _check_origin_sinvoice_edit_line(self):
        for ie in self:
            if ie.sinvoice_edit_type == 'amount':
                if len(ie.sinvoice_edit_line) > len(ie.sinvoice_id.sinvoice_line):
                    raise UserError('Số dòng Hoá đơn Điều chỉnh tiền không được phép nhiều hơn số dòng của Hoá đơn gốc !')
                if '3' in ie.sinvoice_edit_line.mapped('selection'):
                    raise UserError('Hoá đơn chỉnh tiền không hỗ trợ điều chỉnh dòng sản phẩm loại chiết khấu !')

            if ie.sinvoice_id.state == 'edit_amount' and ie.sinvoice_edit_type == 'replace':
                raise UserError('Không thể tạo Hoá đơn thay thế trên Hoá đơn điều chỉnh tiền !')
            if not ie.partner_vat_id and not ie.partner_id:
                raise UserError('Thiếu thông tin khách hàng !')
            # if ie.partner_vat_id and not ie.new_customer_vat:
                # raise UserError('Khách hàng là Đơn vị doanh nghiệp phải có thông tin Mã số thuế !')
            if not ie.customer_address:
                raise UserError('Khách hàng là phải có thông tin Địa chỉ '
                                '(Địa chỉ xuất hoá đơn ưu tiên lấy từ đơn vị)!')
            # Not allow edit customer information if this S-Invoice is editing amount type
            if ie.sinvoice_edit_type not in ('info', 'replace'):
                pair_field_list = [('legal_customer_name', 'new_legal_customer_name'),
                                   ('customer_name', 'new_customer_name'),
                                   ('customer_vat', 'new_customer_vat'),
                                   ('customer_address', 'new_customer_address'),
                                   ('customer_email', 'new_customer_email'),
                                   ('customer_code', 'new_customer_code')]
                changed_fields = []
                for pair in pair_field_list:
                    if getattr(ie, pair[0]) != getattr(ie, pair[1]) and not bool(getattr(ie, pair[0])) != getattr(ie, pair[1]):
                        print(getattr(ie, pair[0]))
                        print(getattr(ie, pair[1]))
                        changed_fields.append(ie.fields_get(pair[0]).get(pair[0], {}).get('string', False))
                if changed_fields:
                    msg = ', '.join(changed_fields)
                    raise UserError('Không được điều chỉnh thông tin khách hàng đối với loại %s.\n'
                                    'Các thông tin đã bị điều chỉnh: %s' %
                                    ({x: y for x, y in EDIT_TYPE}.get(ie.sinvoice_edit_type), msg))

    @api.model
    def default_get(self, fields):
        rec = super(ViettelSinvoiceEdit, self).default_get(fields)
        sinvoice_id = self.env['viettel.sinvoice'].browse(self._context.get('active_id'))
        sinvoice_edit_line_val = []
        for line in sinvoice_id.sinvoice_line:
            sinvoice_edit_line_val.append((0, 0, {
                'selection': line.selection,
                'product_id': line.product_id.id,
                'org_line_id': line.id or False,
                'name': line.name,
                'uom_id': line.uom_id.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'tax_id': line.tax_id and line.tax_id.id or False,
                'price_total': line.price_subtotal,
                'account_id': line.account_id.id,
            }))
        rec.update({
            'sinvoice_id': sinvoice_id.id,
            'partner_vat_id': sinvoice_id.partner_vat_id and sinvoice_id.partner_vat_id.id or False,
            'partner_id': sinvoice_id.partner_id and sinvoice_id.partner_id.id or False,
            # Customer information in the original S-Invoice
            'customer_name': sinvoice_id.customer_name or False,
            'legal_customer_name': sinvoice_id.legal_customer_name or False,
            'customer_code': sinvoice_id.customer_code or False,
            'customer_vat': sinvoice_id.customer_vat or False,
            'customer_email': sinvoice_id.customer_email or False,
            'customer_address': sinvoice_id.customer_address or False,
            # Information S-Invoice
            'viettel_sinvoice_template_id': sinvoice_id.viettel_sinvoice_template_id.id,
            'invoiceIssuedDate': datetime.now(),
            'originalInvoiceId': sinvoice_id.invoiceNo,
            'company_id': sinvoice_id.company_id.id,
            'journal_id': sinvoice_id.journal_id.id,
            'sinvoice_edit_line': sinvoice_edit_line_val,
            'fiscal_position_id': sinvoice_id.fiscal_position_id.id or False,
            'additionalReferenceDesc': self.env['ir.sequence'].next_by_code('sinvoice.reference')
        })
        return rec

    @api.depends('partner_id', 'partner_vat_id')
    def _compute_new_customer_info(self):
        for s in self:
            s.new_customer_name = s.partner_id and s.partner_id.name or False
            s.new_legal_customer_name = s.partner_vat_id and s.partner_vat_id.name or False
            if s.partner_vat_id:
                s.new_customer_code = s.partner_vat_id.ref or False
                s.new_customer_vat = s.partner_vat_id.vat or False
                s.new_customer_address = s.partner_vat_id.vi_full_address or False
            elif s.partner_id:
                s.new_customer_code = s.partner_id.ref or False
                s.new_customer_vat = s.partner_id.vat or False
                s.new_customer_address = s.partner_id.vi_full_address or False
            else:
                s.customer_code = False
                s.customer_vat = False
                s.customer_address = False
            customer_emails = [(s.partner_vat_id and s.partner_vat_id.email or False),
                               (s.partner_id and s.partner_id.email or False)]
            s.new_customer_email = '; '.join([str(el) for el in customer_emails if el and isinstance(el, str)])

    def _prepare_sinvoice_line_values(self):

        sinvoice_edit_type = self.sinvoice_edit_type
        sinvoice_line_val = []
        if sinvoice_edit_type == 'info':
            return sinvoice_line_val
        for line in self.sinvoice_edit_line:
            val = {
                'edit_type': False,
                'selection': line.selection,
                'product_id': line.product_id.id,
                'name': line.name,
                'origin': line.name,
                'account_id': line.account_id.id,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'discount': line.discount,
                'uom_id': line.product_id.uom_id.id,
                'tax_id': line.tax_id and line.tax_id.id or False,
            }
            if sinvoice_edit_type == 'amount':
                val['edit_type'] = line.edit_type
                val['org_line_id'] = line.org_line_id.id
            sinvoice_line_val.append((0, 0, val))
        return sinvoice_line_val

    def create_new_sinvoice(self, sinvoice_id):
        adjustmentType = ''
        adjustmentInvoiceType = ''
        if self.sinvoice_edit_type == 'replace':
            adjustmentType = '3'
        elif self.sinvoice_edit_type == 'amount':
            adjustmentType = '5'
            adjustmentInvoiceType = '1'
        elif self.sinvoice_edit_type == 'info':
            adjustmentType = '5'
            adjustmentInvoiceType = '2'
        sinvoice_val = {
            'base_sinvoice_id': sinvoice_id.id,
            'viettel_sinvoice_template_id': sinvoice_id.viettel_sinvoice_template_id.id,
            'company_id': sinvoice_id.company_id.id,
            'currency_id': sinvoice_id.currency_id.id,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'partner_vat_id': self.partner_vat_id and self.partner_vat_id.id or False,
            'date_invoice': self.invoiceIssuedDate,
            'date': self.invoiceIssuedDate,
            'company_currency_id': sinvoice_id.company_currency_id.id,
            'journal_id': self.journal_id.id,
            'fiscal_position_id': sinvoice_id.fiscal_position_id and sinvoice_id.fiscal_position_id.id,
            'internal_move_type': sinvoice_id.internal_move_type,
            'adjustmentType': adjustmentType,
            'invoice_ids': [(4, move.id) for move in sinvoice_id.invoice_ids],
            'ref': self.sinvoice_id.ref,
            'additionalReferenceDesc': self.additionalReferenceDesc,
            'additionalReferenceDate': self.additionalReferenceDate,
            'invoiceIssuedDate': self.invoiceIssuedDate
        }
        if adjustmentInvoiceType:
            sinvoice_val['adjustmentInvoiceType'] = adjustmentInvoiceType

        sinvoice_line_vals = self._prepare_sinvoice_line_values()
        if sinvoice_line_vals:
            sinvoice_val.update({
                'sinvoice_line': sinvoice_line_vals
            })
        new_sinvoice_id = self.env['viettel.sinvoice'].create(sinvoice_val)
        return new_sinvoice_id

    def action_edit_sinvoice(self):
        # Check validate to action
        sinvoice_id = self.sinvoice_id

        if sinvoice_id.state == 'is_edited_info' and self.sinvoice_edit_type == 'info':
            info_sinv = self.env['viettel.sinvoice'].search(
                [('state', '=', 'edit_info'), ('state', 'not in', ('canceled', 'draft', 'confirm')),
                 ('base_sinvoice_id', '=', sinvoice_id.id)])
            if info_sinv:
                raise UserError('HĐĐT này đã điều chỉnh thông tin một lần!\n'
                                'Bạn cần huỷ Hoá đơn điều chỉnh thông tin trước đó để tạo lại một Hoá đơn chỉnh sửa thông tin khác !')
        if sinvoice_id.state in ('canceled', 'is_replaced', 'edit_info'):
            raise UserError(
                'Bạn không thể cập nhật Hoá đơn ở các trạng thái: Đã huỷ, Bị thay thế, Chỉnh sửa thông tin !')

        # Create new S-Invoice Data and send request to S-Invoice Service
        new_sinvoice_id = self.create_new_sinvoice(self.sinvoice_id)
        action = {'type': 'ir.actions.act_window_close'}
        return action


class ViettelSInvoiceLineEdit(models.TransientModel):
    _name = 'viettel.sinvoice.line.edit'
    _description = 'Viettel S-Invoice Line Edit'

    @api.depends('price_unit', 'discount', 'tax_id', 'quantity',
                 'product_id', 'sinvoice_id.partner_vat_id', 'sinvoice_id.currency_id', 'sinvoice_id.company_id',
                 'sinvoice_id.date_invoice', 'sinvoice_id.date')
    def _compute_price(self):
        for line in self:
            currency = line.sinvoice_id and line.sinvoice_id.currency_id
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, currency, line.quantity, product=line.product_id,
                                                          partner=line.sinvoice_id.partner_vat_id)
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

    sinvoice_edit_id = fields.Many2one('viettel.sinvoice.edit', string='S-Invoice Edit', required=True)
    sinvoice_id = fields.Many2one('viettel.sinvoice', string='Invoice Reference',
                                  related='sinvoice_edit_id.sinvoice_id', required=True)
    edit_type = fields.Selection([('increase', 'Tăng'), ('reduction', 'Giảm')], string='Edit Type',
                                 compute='_compute_edit_type', store=True)
    selection = fields.Selection(LINE_SELECTION, string='Selection', default='1', required=True)
    sinvoice_edit_type = fields.Selection(related='sinvoice_edit_id.sinvoice_edit_type')
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', index=True)
    name = fields.Text(string='Description', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                             ondelete='set null', index=True)
    quantity = fields.Float(string='Quantity', default=1)
    price_unit = fields.Float(string='Unit Price')
    tax_id = fields.Many2one('account.tax', string='Taxes',
                                           domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                                                   ('active', '=', True)])
    discount = fields.Float(string='Discount (%)', default=0.0)
    price_subtotal = fields.Float(string='Total', store=True, readonly=True, compute='_compute_price',
                                  help="Total amount without taxes")
    price_total = fields.Float(string='Amount (with Taxes)', store=True, readonly=True, compute='_compute_price',
                               help="Total amount with taxes")
    price_subtotal_signed = fields.Float(string='Amount Signed', store=True, readonly=True, compute='_compute_price',
                                         help="Total amount in the currency of the company, negative for credit note.")
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_price', store=True)
    price_discount = fields.Monetary(string='Price Discount', compute='_compute_price', store=True)
    account_id = fields.Many2one('account.account', string='Account')
    company_id = fields.Many2one('res.company', string='Company', related='sinvoice_id.company_id', store=True,
                                 readonly=True, related_sudo=False)
    currency_id = fields.Many2one('res.currency', related='sinvoice_id.currency_id', store=True, related_sudo=False,
                                  readonly=False)
    org_line_id = fields.Many2one('viettel.sinvoice.line', 'Original Line',
                                  domain="[('sinvoice_id','=',sinvoice_id), ('selection', '=', '1')]")

    @api.constrains('sinvoice_edit_id', 'sinvoice_edit_id', 'org_line_id', 'edit_type', 'price_unit')
    def _check_origin_sinvoice_line(self):
        for line in self:
            if float_compare(line.quantity, 0, 0) == -1:
                raise UserError('Số lượng sản phẩm phải là số dương !')
            if line.sinvoice_edit_id.sinvoice_edit_type == 'amount':
                if not line.org_line_id:
                    raise UserError('Dòng hoá đơn chỉnh sửa phải khai báo dòng hoá đơn gốc!')
                if not line.edit_type:
                    raise UserError('Loại điều chỉnh tăng giảm bắt buộc đối với Hoá đơn điều chỉnh tiền !')
                if not line.org_line_id:
                    raise UserError('Bắt buộc chọn dòng cần chỉnh sửa từ hoá đơn điện tử gốc !')
                if line.org_line_id.product_id != line.product_id:
                    raise UserError('Không được điều chỉnh sản phẩm khác trên hoá đơn chỉnh sửa tiền !')
                if line.org_line_id.name != line.name:
                    raise UserError('Tên sản phẩm không được phép thay đổi trên hoá đơn chỉnh sửa tiền !')
                if line.org_line_id.quantity != line.quantity:
                    raise UserError('Số lượng sản phẩm không được phép thay đổi trên Hoá đơn chỉnh sửa tiền !')
                if float_compare(line.price_unit, 0, 0) == 0:
                    raise UserError('Đơn giá điều chỉnh không được bằng không !')
            else:
                if float_compare(line.price_total, 0, 0) == -1 and line.selection != '3':
                    raise UserError('Thành tiền phải là số dương đối với dòng sản phẩm là Hàng hoá của Hoá đơn thay thế !')

    @api.depends('sinvoice_edit_id.sinvoice_edit_type', 'price_unit')
    def _compute_edit_type(self):
        for line in self:
            if line.sinvoice_edit_id.sinvoice_edit_type == 'amount':
                if float_compare(line.price_unit, 0, 0) == -1:
                    line.edit_type = 'reduction'
                else:
                    line.edit_type = 'increase'
            else:
                line.edit_type = False

    @api.onchange('product_id', 'price_unit')
    def _onchange_product_id(self):
        if not self.sinvoice_id:
            return

        partner_vat_id = self.sinvoice_id.partner_vat_id
        partner_id = self.sinvoice_id.partner_id
        if not partner_vat_id and not partner_id:
            warning = {
                'title': _('Warning!'),
                'message': _('You must first select a partner.'),
            }
            return {'warning': warning}

        else:
            self_lang = self
            if partner_vat_id.lang:
                self_lang = self.with_context(lang=partner_vat_id.lang)

            company_id = self.company_id or self.env.user.company_id
            taxes = self.product_id.taxes_id.filtered(lambda r: r.company_id == company_id) \
                    or self.account_id.tax_ids or self.sinvoice_id.company_id.account_sale_tax_id
            tax = self.sinvoice_id.fiscal_position_id.map_tax(taxes)
            if tax:
                self.tax_id = tax[0] or False
            product = self_lang.product_id
            self.name = product.name

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id

            if self.uom_id and self.uom_id.id != product.uom_id.id:
                self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
