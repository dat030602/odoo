# -*- coding: utf-8 -*-

from datetime import datetime
import time
import pprint

from requests.adapters import HTTPAdapter

from odoo import models, fields, api, _
import requests
import json
from odoo.exceptions import UserError, AccessError
import uuid
import logging

from odoo.tools import float_compare
from .share_func import amount_to_text

_logger = logging.getLogger(__name__)

ADJUSTMENT_TYPE = [
    ('1', 'Hóa đơn gốc'),
    ('3', 'Hóa đơn thay thế'),
    ('5', 'Hóa đơn điều chỉnh'),
    ('7', 'Hóa đơn xóa bỏ')
]

ADJUSTMENT_INVOICE_TYPE = [
    ('1', 'Hoá đơn điều chỉnh tiền'),
    ('2', 'Hoá đơn điều chỉnh thông tin')
]

DEFAULT_HEADER = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8'
}


class ViettelSInvoice(models.Model):
    _name = "viettel.sinvoice"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Viettel S-Invoice"
    _order = "id desc"

    def _get_default_invoiceType(self):
        return self.env.ref('viettel_sinvoice.vsi_type_03XKNB')

    def get_command_of(self):
        return self.env.company.name

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id

    @api.model
    def _default_journal(self):
        company_id = self._context.get('company_id', self.env.company.id)
        return self.env['account.journal'].search([('company_id', '=', company_id), ('type', '=', 'sale')], limit=1)

    @api.depends('sinvoice_line.price_subtotal', 'sinvoice_line.price_tax')
    def _compute_amount(self):
        for s in self:
            s.amount_untaxed = round(sum(line.price_subtotal for line in s.sinvoice_line.filtered(
                lambda l: l.selection in ('1', '3'))), 0)
            s.amount_tax = round(sum(line.price_tax for line in s.sinvoice_line.filtered(
                lambda l: l.selection in ('1', '3'))), 0)
            s.amount_total = s.amount_untaxed + s.amount_tax
            s.amount_discount = round(sum(line.price_discount for line in s.sinvoice_line.filtered(
                lambda l: l.selection in ('1', '3'))), 0)

    name = fields.Char('Name', readonly=True, copy=False, default='New')
    # invoice_id = fields.Many2one('account.move', string='Odoo Invoice')
    invoice_ids = fields.Many2many(
        'account.move', 'viettel_sinvoice_account_rel', string='Invoices', readonly=True)
    base_sinvoice_id = fields.Many2one('viettel.sinvoice', string='Base S-invoice')
    inherited_sinvoice_ids = fields.One2many('viettel.sinvoice', compute='_compute_inherited_sinvoice_ids',
                                             string='Child S-Invoice')
    inherited_sinvoice_count = fields.Integer('S-Invoices', compute='_compute_inherited_sinvoice_ids')
    ref = fields.Char('Reference', readonly=True)
    internal_move_type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        # ('out_refund', 'Customer Credit Note'),
        # ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        # ('out_receipt', 'Sales Receipt'),
        # ('in_receipt', 'Purchase Receipt'),
    ], readonly=True, string='Internal Invoice Type')

    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env['res.company']._company_default_get('account.move'))
    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.user, copy=False)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True, default=_default_journal)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, default=_default_currency, tracking=True)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)

    partner_id = fields.Many2one('res.partner', 'S-Invoice Contact', tracking=True)
    partner_vat_id = fields.Many2one('res.partner', 'Legal S-invoice Customer', tracking=True, domain="[('is_company','=',True)]")
    # Customer Information
    customer_name = fields.Char('Contact Name', compute='_compute_customer_info', store=True)
    legal_customer_name = fields.Char('S-Invoice Customer Name', compute='_compute_customer_info', store=True)
    customer_code = fields.Char('Customer Code', compute='_compute_customer_info', store=True)
    customer_vat = fields.Char('VAT', compute='_compute_customer_info', store=True)
    customer_address = fields.Char('VAT Address', compute='_compute_customer_info', store=True)
    customer_email = fields.Char('Customer Emails', compute='_compute_customer_info', store=True)
    is_individual_customer = fields.Boolean(compute='_compute_customer_info', store=True)
    customer_budget_code = fields.Char(compute='_compute_customer_info', store=True)
    customer_id_no = fields.Char(compute='_compute_customer_info', store=True)
    additional_emails = fields.Char('Additional Emails')

    sinvoice_line = fields.One2many('viettel.sinvoice.line', 'sinvoice_id', copy=True)
    date_invoice = fields.Date(string='Invoice Date', index=True, copy=False)
    date = fields.Date(string='Accounting Date', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('created', 'Created'),
        ('canceled', 'Canceled'),
        ('edit_info', 'Edit Info'),
        ('is_edited_info', 'Is Edited Info'),
        ('edit_amount', 'Edit Amount'),
        ('is_edited_amount', 'Is Edited Amount'),
        ('replace', 'Replace'),
        ('is_replaced', 'Is Replaced'),
    ], string='Status', copy=False, default='draft', readonly=True, tracking=True)

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_compute_amount', copy=False)
    amount_tax = fields.Monetary(string='Tax', store=True, readonly=True, compute='_compute_amount', copy=False)
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_amount', copy=False)
    amount_discount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_compute_amount', copy=False)
    viettel_sinvoice_template_id  = fields.Many2one('viettel.sinvoice.template', 'Config Template', copy=True, readonly=True)  # Cấu hình mẫu hoá đơn
    branch_id = fields.Many2one('company.branch', related='viettel_sinvoice_template_id.branch_id', string='Branch')
    supplierTaxCode = fields.Char('Supplier Tax Code', related='viettel_sinvoice_template_id.vat', store=True, tracking=True)
    invoiceType = fields.Many2one('viettel.sinvoice.type', string='Type', related='viettel_sinvoice_template_id.type_id', store=True)  # Mã loại hóa đơn
    templateCode = fields.Char('Template Code', related='viettel_sinvoice_template_id.template_code', store=True)
    invoiceSeries = fields.Char('Invoice Series', related='viettel_sinvoice_template_id.series', store=True)
    invoiceIssuedDate = fields.Datetime('Invoice Issued Date', copy=False, readonly=True)
    currencyCode = fields.Char("Currency Code", related='currency_id.name')
    adjustmentType = fields.Selection(ADJUSTMENT_TYPE, string='Adjustment Type', default='1', required=True, tracking=True, copy=False)
    adjustmentInvoiceType = fields.Selection(ADJUSTMENT_INVOICE_TYPE, string='Adjustment Invoice Type', copy=False, default=False)
    invoiceNo = fields.Char('Invoice No', readonly=True)
    code_of_tax = fields.Char('Code of Tax', readonly=True)
    originalInvoiceIssueDate = fields.Datetime('Original Invoice Issue Date', copy=False)  # Thời gian phát hành hóa đơn gốc
    additionalReferenceDesc = fields.Char('Additional Reference Description', readonly=True, copy=False)
    additionalReferenceDate = fields.Datetime('Additional Reference Date', readonly=True, copy=False)
    reason = fields.Text('Delete Reason', readonly=True, copy=False)
    # Payment Information
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    paymentMethodName = fields.Selection([
        ('TM', 'TM'),
        ('CK', 'CK'),
        ('TM/CK', 'TM/CK')
    ], string='Payment Method', default='TM/CK')
    paymentStatus = fields.Boolean('Paid', default=True)

    cusGetInvoiceRight = fields.Boolean('Customer Get Invoice Right', default=True)
    exchangeRate = fields.Float('Exchange Rate', copy=False)
    transactionID = fields.Char('Transaction ID', readonly=True, copy=False)
    reservationCode = fields.Char('Reservation Code', readonly=True, copy=False)
    userName = fields.Char(related='user_id.name', string='User Name')
    cancel_desc = fields.Char('Cancel Note', copy=False)
    attachment_ids = fields.Many2many('ir.attachment', 'sinvoice_ir_attachments_rel', 'sinvoice_id', 'attachment_id', string='Attachments', copy=False)
    downloaded = fields.Boolean("Downloaded", default=False, compute='_compute_download_pdf')
    note = fields.Text('Note', readonly=True, copy=False)
    refund_note = fields.Text('Refund Note', tracking=True, copy=False)
    # Thông tin Hoá đơn xuất kho kiêm vận chuyển nội bộ
    picking_id = fields.Many2one('stock.picking', 'Stock Picking', readonly=True, copy=False)
    invoice_type_code = fields.Char(related='invoiceType.code', readonly=True)

    invoices_total = fields.Monetary('Invoices Total', compute='_compute_invoices_total', store=True)
    invoice_sinvoice_diff = fields.Float('Sinvoice Diff', compute='_compute_invoices_total', store=True)

    @api.constrains('partner_id', 'partner_vat_id', 'customer_address', 'customer_vat')
    def check_required_field_partner(self):
        for s in self:
            if not s.partner_vat_id and not s.partner_id:
                raise UserError('Thiếu thông tin khách hàng !')
            # if s.partner_vat_id and not s.customer_vat:
            #     raise UserError('Khách hàng là Đơn vị doanh nghiệp phải có thông tin Mã số thuế !')
            if not s.customer_address:
                raise UserError('Khách hàng là phải có thông tin Địa chỉ !')
            taxes = s.sinvoice_line.filtered(lambda x: x.selection in ('1', '3')).mapped('tax_id')
            if len(set(taxes)) > 1:
                raise UserError('Phải sử dụng một loại thuế duy nhất trên cùng một hóa đơn điện tử!')

    @api.depends('name', 'invoice_ids.name')
    def _compute_display_name(self):
        for sinv in self:
            ref = ' '.join(sinv.mapped('invoice_ids.name')) if sinv.invoice_ids else sinv.ref or ''
            if ref:
                display_name = sinv.name or '' + ' - %s' % ref
            else:
                display_name = sinv.name
            sinv.display_name = display_name

    @api.depends('invoice_ids', 'invoice_ids.amount_total_signed')
    def _compute_invoices_total(self):
        for rec in self:
            if not self.invoice_ids:
                rec.invoices_total = 0.0
                rec.invoice_sinvoice_diff = 0.0
            else:
                invoices_total = sum(rec.mapped('invoice_ids.amount_total_signed'))
                rec.invoices_total = invoices_total
                rec.invoice_sinvoice_diff = invoices_total - rec.amount_total

    @api.depends('partner_id', 'partner_vat_id')
    def _compute_customer_info(self):
        for s in self:
            s.customer_name = s.partner_id.name
            s.legal_customer_name = s.partner_vat_id.name
            if s.partner_vat_id:
                s.is_individual_customer = False
                s.customer_code = s.partner_vat_id.ref
                s.customer_vat = s.partner_vat_id.vat
                s.customer_address = s.partner_vat_id.vi_full_address
                s.customer_budget_code = s.partner_vat_id.budget_code
                s.customer_id_no = s.partner_vat_id.identification_no
            elif s.partner_id:
                s.is_individual_customer = True
                s.customer_code = s.partner_id.ref
                s.customer_vat = s.partner_id.vat
                s.customer_address = s.partner_id.vi_full_address
                s.customer_budget_code = s.partner_id.budget_code
                s.customer_id_no = s.partner_id.identification_no
            else:
                s.customer_code = False
                s.customer_vat = False
                s.customer_address = False
                s.customer_budget_code = False
                s.customer_id_no = False
            customer_emails = []
            if s.partner_vat_id and s.partner_vat_id.email:
                customer_emails.append(s.partner_vat_id.email)
            if s.partner_id and s.partner_id.email:
                customer_emails.append(s.partner_id.email)
            s.customer_email = '; '.join(customer_emails)
            if not s.fiscal_position_id:
                s.fiscal_position_id = (s.partner_vat_id.property_account_position_id and self.partner_vat_id.property_account_position_id.id) \
                                        or (s.partner_id.property_account_position_id and self.partner_id.property_account_position_id.id)

    def get_children_sinv(self, obj):
        def _parent(obj, lst):
            children = self.search([('base_sinvoice_id', 'in', obj.ids)])
            if children:
                lst += children.ids
                _parent(children, lst)
            else:
                return lst
        rslt = []
        _parent(self, rslt)
        return rslt

    def _compute_inherited_sinvoice_ids(self):
        for s in self:
            sinv_ids = self.get_children_sinv(s)
            s.inherited_sinvoice_ids = self.browse(sinv_ids)
            s.inherited_sinvoice_count = len(s.inherited_sinvoice_ids)

    def _compute_download_pdf(self):
        for s in self:
            s.downloaded = bool(s.attachment_ids)

    def action_view_inherited_sinvoice(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('viettel_sinvoice.action_open_viettel_sinvoice')
        action['domain'] = [('id', 'in', self.mapped('inherited_sinvoice_ids.id'))]
        action['context'] = dict(self._context, create=False)
        return action

    def _get_currency_rate_date(self):
        return self.date or self.date_invoice

    def unlink(self):
        for s in self:
            if s.state == 'confirm':
                raise UserError('Không thể xoá S-Invoice đã xác nhận !')
            elif s.state != 'draft':
                raise UserError('Không thể xoá S-Invoice đã phát hành !')
        return super(ViettelSInvoice, self).unlink()

    @api.model
    def create(self, vals_list):
        if not vals_list.get('transactionID'):
            vals_list['transactionID'] = str(uuid.uuid4())
        res = super(ViettelSInvoice, self).create(vals_list)
        return res

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def _get_general_invoice_info(self):
        if not self.invoiceType:
            raise UserError('Chưa thiết lập loại hoá đơn trên trong phần thông tin cấu hình "Viettel S-Invoice"'
                            'của công ty: %s.\n Xin vui lòng liên hệ đến Quản trị viên!' % self.company_id.name)
        issue_date_tmp = int(self.invoiceIssuedDate.timestamp()) * 1000
        transactionID = self.transactionID or str(uuid.uuid4())
        if not self.transactionID:
            self.transactionID = transactionID
        data = {
            'transactionUuid': transactionID,
            'invoiceType': self.invoiceType.code,
            'templateCode': self.templateCode,
            'invoiceSeries': self.invoiceSeries,
            'invoiceIssuedDate': issue_date_tmp,
            'currencyCode': self.currency_id.name,
            'adjustmentType': self.adjustmentType,
            'paymentStatus': True,  # TODO: the status always is paid, ignore value of this field
            'cusGetInvoiceRight': self.cusGetInvoiceRight,
            'userName': self.user_id.name,
        }
        if self.adjustmentType in ('3', '5'):
            org_issue_date_tmp = int(self.base_sinvoice_id.invoiceIssuedDate.timestamp()) * 1000
            add_ref_date_tmp = int(self.additionalReferenceDate.timestamp()) * 1000
            data['originalInvoiceId'] = self.base_sinvoice_id.name
            data['originalInvoiceIssueDate'] = org_issue_date_tmp
            data['additionalReferenceDesc'] = self.additionalReferenceDesc
            data['additionalReferenceDate'] = add_ref_date_tmp
            data['invoiceSignedDate'] = issue_date_tmp
            if self.adjustmentInvoiceType:
                data['adjustmentInvoiceType'] = self.adjustmentInvoiceType
        return data

    def _get_sinvoice_item_data(self):

        self.ensure_one()
        amount_total = 0.0
        ref_dit_type = {'increase': 'tăng', 'reduction': 'giảm'}
        templateCode = self.templateCode
        invoiceSeries = self.invoiceSeries
        sinvoice_items = []
        edit_notes = []
        if any(sel in self.sinvoice_line.mapped('selection') for sel in ('4', '5')):
                raise UserError('Chỉ hỗ trợ tạo Hoá đơn điện tử với dòng sản phẩm là loại "Hàng hoá", "Chiết khấu" và "Ghi chú"!')
        lineNumber = 0
        for line in self.sinvoice_line.filtered(lambda x: x.selection in ('1', '3')):
            if self.adjustmentType == '5' and self.adjustmentInvoiceType == '2':
                break
            if line.selection not in ('1', '3'):
                raise UserError('Chỉ hỗ trợ tạo Hoá đơn điện tử với dòng sản phẩm là loại "Hàng hoá" và "Chiết khấu"!')
            if line.discount:
                raise UserError('Không hỗ trợ hóa đơn có dòng cột chiếc khấu!\n'
                                'Giá chiết khấu phải trừ trực tiếp vào đơn giá của sản phẩm.')
            lineNumber += 1
            item = {
                'lineNumber': lineNumber,
                'itemCode': line.product_id.default_code or '',
                'itemName': line.name,
                'unitName': line.uom_id.name or '',
                'unitPrice': abs(line.price_unit),
                'quantity': line.quantity,
                'itemTotalAmountWithoutTax': abs(round(line.price_unit * line.quantity, 0)),
                'itemTotalAmountWithTax': abs(round(line.price_total, 0)),
                'itemTotalAmountAfterDiscount': abs(round(line.price_subtotal, 0)),
                'taxAmount': abs(round(line.price_tax, 0)),
                'taxPercentage': -2,
                'discount': 0.0,  # TODO: default not use discount field in template line.discount,
                'itemDiscount': round(line.price_discount, 0)
            }
            if line.tax_id:
                item['taxPercentage'] = line.tax_id.amount
            # Hoá đơn xuất kho kiêm vận chuyển nội bộ
            elif line.sinvoice_id.invoiceType.code == '03XKNB':
                item['taxPercentage'] = -1

            # FIXME: thêm dòng note hàng KM không thu tiền, taxAmount = 0 nếu đơn giá bằng 0
            if line.selection == '3':
                item['selection'] = 3
                item['isIncreaseItem'] = False

            if self.adjustmentType == '5' and self.adjustmentInvoiceType == '1':
                if not line.edit_type:
                    raise UserError('Loại điều chỉnh tăng giảm là bắt buộc !')

                if line.edit_type not in edit_notes:
                    edit_notes.append(ref_dit_type[line.edit_type])

                if line.edit_type == 'increase':
                    is_increase = True
                    detail_name = 'Điều chỉnh tăng tiền hàng, tiền thuế của hàng hóa/dịch vụ: %s' % line.org_line_id.name
                else:
                    is_increase = False
                    detail_name = 'Điều chỉnh giảm tiền hàng, tiền thuế của hàng hóa/dịch vụ: %s' % line.org_line_id.name
                item['isIncreaseItem'] = is_increase
                item['itemName'] = detail_name
                item['adjustmentTaxAmount'] = 1
            sinvoice_items.append(item)
            amount_total += line.price_total

        # Prepare line that's the note type
        for line in self.sinvoice_line.filtered(lambda x: x.selection == '2'):
            lineNumber += 1
            note_line = {
                'selection': 2,
                'itemName': line.name,
                'lineNumber': lineNumber
            }
            sinvoice_items.append(note_line)

        if self.adjustmentType == '1' and self.internal_move_type == 'in_refund' and self.refund_note:
            additional_line = {
                'selection': 2,
                'itemName': self.refund_note
            }
            sinvoice_items.append(additional_line)

        elif self.adjustmentType == '3':
            note = "Hóa đơn thay thế cho hóa đơn điện tử số %s lập ngày %s" % (
                self.base_sinvoice_id.name,
                self.base_sinvoice_id.invoiceIssuedDate.strftime("%d/%m/%Y")
            )
            additional_line = {
                'selection': 2,
                'itemName': note
            }
            sinvoice_items.append(additional_line)
            self.note = note
        elif self.adjustmentType == '5':
            base_sinv_id = self.base_sinvoice_id
            str_org_sinv_id = base_sinv_id.invoiceIssuedDate.strftime("%d/%m/%Y")
            if self.adjustmentInvoiceType == '2':
                note = "Điều chỉnh thông tin khách hàng cho hóa đơn điện tử mẫu %s ký hiệu %s số %s lập ngày %s:" % (
                    templateCode, invoiceSeries, base_sinv_id.name, str_org_sinv_id)
                info_items = []
                if base_sinv_id.customer_name != self.customer_name:
                    info_items.append('Tên người mua: %s-->%s' % (base_sinv_id.customer_name, self.customer_name))
                if base_sinv_id.customer_code != self.customer_code:
                    info_items.append('Mã khách hàng: %s-->%s' % (base_sinv_id.customer_code, self.customer_code))
                if base_sinv_id.customer_vat != self.customer_vat:
                    raise UserError('Mã số thuế không được phép thay đổi !')
                if base_sinv_id.customer_address != self.customer_address:
                    info_items.append('Địa chỉ: %s-->%s' % (base_sinv_id.customer_address, self.customer_address))
                if base_sinv_id.customer_email != self.customer_email:
                    info_items.append('Địa chỉ Email: %s-->%s' % (base_sinv_id.customer_email, self.customer_email))
                if base_sinv_id.legal_customer_name != self.legal_customer_name:
                    info_items.append(
                        'Tên đơn vị: %s-->%s' % (base_sinv_id.legal_customer_name, self.legal_customer_name))
                if info_items:
                    note = '%s %s' % (note, ';'.join(info_items))
                add_edit_info_line = {
                    'selection': 2,
                    'itemName': note
                }
                sinvoice_items.append(add_edit_info_line)
                self.note = note
            elif self.adjustmentInvoiceType == '1':
                base_sinv_id = self.base_sinvoice_id
                str_org_sinv_issued_date = base_sinv_id.invoiceIssuedDate.strftime("%d/%m/%Y")
                add_edit_amount_line = {
                    "selection": 2,
                    "itemName": "Điều chỉnh %s tiền hàng, tiền thuế cho hóa đơn điện tử số %s lập ngày %s số tiền: %s" %
                                (edit_notes and "%s" % '/'.join(edit_notes) or "",
                                 base_sinv_id.name, str_org_sinv_issued_date, abs(amount_total))
                }
                self.note = add_edit_amount_line.get('itemName')
                sinvoice_items.append(add_edit_amount_line)
        return sinvoice_items

    def _get_buyer_info(self):
        buyer_info = {
            'buyerName': self.customer_name or '',
            'buyerLegalName': self.legal_customer_name or '',
            'buyerAddressLine': self.customer_address or '',
            'buyerCode': self.customer_code or '',
            'buyerBudgetCode': self.customer_budget_code or '',
        }
        if self.customer_vat:
            buyer_info.update({'buyerTaxCode': self.customer_vat})
        if self.customer_email:
            emails = self.customer_email
            if self.additional_emails:
                emails = emails + ';' + self.additional_emails
            buyer_info.update({'buyerEmail': emails})
        if self.customer_id_no:
            buyer_info.update({
                'buyerIdType': '1',
                'buyerIdNo': self.customer_id_no
            })
        return buyer_info

    def _get_summarize_sinvoice_info(self):
        """
        Validate parameter before calling the method
            'sumOfTotalLineAmountWithoutTax': 0.0,
            'totalAmountWithoutTax': 0.0,
            'totalTaxAmount': 0.0,
            'totalAmountWithTax': 0.0,
            'discountAmount': 0.0
        """
        if self.adjustmentType == '5' and self.adjustmentInvoiceType == '2':
            return {}
        values = {
            'sumOfTotalLineAmountWithoutTax': 0.0,
            'totalAmountWithoutTax': 0.0,
            'totalTaxAmount': 0.0,
            'totalAmountWithTax': 0.0,
            'discountAmount': 0.0
        }
        for item in self.sinvoice_line:
            if item.price_unit and item.quantity and item.selection in ('1', '3'):
                values['sumOfTotalLineAmountWithoutTax'] += round(item.price_unit * item.quantity, 0)
                values['totalAmountWithoutTax'] += round(item.price_subtotal, 0)
                values['totalTaxAmount'] += round(item.price_tax, 0)
                values['totalAmountWithTax'] += round(item.price_total, 0)
                values['discountAmount'] += round(item.price_discount, 0)
        for key in values:
            values[key] = abs(round(values[key], 0))
        if self.adjustmentType == '5' and self.adjustmentInvoiceType == '1':
            values.update({
                "isTotalAmountPos": self.amount_total >= 0 and True or False,
                "isTotalTaxAmountPos": self.amount_tax >= 0 and True or False,
                "isTotalAmtWithoutTaxPos": self.amount_untaxed >= 0 and True or False,
                "isDiscountAmtPos": self.amount_discount >= 0 and True or False
            })
        return values

    def _get_tax_breakdown(self):
        tax_breakdown = {}
        for line in self.sinvoice_line.filtered(lambda l: l.selection in ('1', '3')):
            if line.tax_id:
                tax_id = line.tax_id
                if tax_id.id not in tax_breakdown:
                    tax_breakdown[tax_id.id] = {
                        'taxPercentage': tax_id.amount,
                        'taxableAmount': round(line.price_subtotal, 0),
                        'taxAmount': round(line.price_tax, 0)
                    }
                else:
                    tax_breakdown[tax_id.id]['taxableAmount'] += line.price_subtotal
                    tax_breakdown[tax_id.id]['taxAmount'] += line.price_tax
            elif line.sinvoice_id.invoiceType.code == '03XKNB':
                if -1 not in tax_breakdown:
                    tax_breakdown[-1] = {
                        'taxPercentage': -1,
                        'taxableAmount': round(line.price_subtotal, 0),
                        'taxAmount': round(line.price_tax, 0)
                    }
                else:
                    tax_breakdown[-1]['taxableAmount'] += line.price_subtotal
                    tax_breakdown[-1]['taxAmount'] += line.price_tax
            # Không chịu thuế
            else:
                if -2 not in tax_breakdown:
                    tax_breakdown[-2] = {
                        'taxPercentage': -2,
                        'taxableAmount': round(line.price_subtotal, 0),
                        'taxAmount': round(line.price_tax, 0)
                    }
                else:
                    tax_breakdown[-2]['taxableAmount'] += line.price_subtotal
                    tax_breakdown[-2]['taxAmount'] += line.price_tax

        tax_list = list(tax_breakdown.values())
        rslt = []
        for tax in tax_list:
            element = {}
            if tax['taxAmount']:
                element['taxAmountPos'] = tax['taxAmount'] > 0 and True or False
            element.update({key: key not in ('taxPercentage', 'taxAmountPos') and abs(tax[key]) or tax[key] for key in tax})
            rslt.append(element)
        return rslt
    # FIXME: taxAmountPos

    def _get_payments(self):
        return [{
            "paymentMethodName": self.paymentMethodName or 'TM/CK',
        }]

    def _get_meta_data(self):
        """
        Override this method to customize metadata.
        Returns a list of metadata dictionaries for the API.
        First checks if there's a picking_id or invoice_ids, and calls their _get_meta_data methods.
        """
        # Check if created from picking
        if self.picking_id:
            meta = self.picking_id._get_meta_data()
            # If meta is a dict (for initialization), convert to list format for API
            if isinstance(meta, dict):
                return []
            return meta if isinstance(meta, list) else []
        # Check if created from account move
        if self.invoice_ids:
            # Use the first invoice's _get_meta_data
            meta = self.invoice_ids[0]._get_meta_data()
            # If meta is a dict (for initialization), convert to list format for API
            if isinstance(meta, dict):
                return []
            return meta if isinstance(meta, list) else []
        return []

    def _prepare_data_to_send_sinvoice(self):

        general_invoice_info = self._get_general_invoice_info()
        invoice_items = self._get_sinvoice_item_data()
        if not invoice_items:
            raise UserError('Không có thông tin sản phẩm để Xuất hoá đơn !')

        rslt = {
            'generalInvoiceInfo': general_invoice_info,
            'buyerInfo': self._get_buyer_info(),
            'summarizeInfo': self._get_summarize_sinvoice_info(),
            'taxBreakdowns': self._get_tax_breakdown(),
            'itemInfo': invoice_items,
            'payments': self._get_payments(),
            'metadata': self._get_meta_data(),
        }
        return rslt

    def _prepare_data_to_send_sinvoice_edit(self):
        rslt = {
            'generalInvoiceInfo': self._get_general_invoice_info(),
            'buyerInfo': self._get_buyer_info(),
            'summarizeInfo': self._get_summarize_sinvoice_info(),
            'taxBreakdowns': self._get_tax_breakdown(),
            'itemInfo': self._get_sinvoice_item_data(),
            'payments': self._get_payments()
        }
        return rslt

    def update_sinvoice_after_send_request(self, resp_rslt):

        self.ensure_one()
        current_val = {
            'supplierTaxCode': resp_rslt['supplierTaxCode'],
            'name': resp_rslt['invoiceNo'],
            'invoiceNo': resp_rslt['invoiceNo'],
            'reservationCode': resp_rslt['reservationCode']
        }
        if resp_rslt.get('transactionID'):
            current_val['transactionID'] = resp_rslt.get('transactionID')
        base_vals = {}
        if self.adjustmentType == '1':
            current_val.update({'state': 'created'})
        elif self.adjustmentType == '3':
            current_val.update({'state': 'replace'})
            base_vals = {'state': 'is_replaced'}
        elif self.adjustmentType == '5':
            if self.adjustmentInvoiceType == '2':
                current_val.update({'state': 'edit_info'})
                base_vals = {'state': 'is_edited_info'}
            elif self.adjustmentInvoiceType == '1':
                current_val.update({'state': 'edit_amount'})
                base_vals = {'state': 'is_edited_amount'}
        self.write(current_val)
        if base_vals:
            self.base_sinvoice_id.write(base_vals)

    # Update Information
    def action_check_invoice_by_transactionID(self, raise_error=True):
        url = self.company_id.vsi_domain + '/InvoiceAPI/InvoiceWS/searchInvoiceByTransactionUuid'
        access_token = self.company_id.get_access_token()
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        headers = {**headers, 'Cookie': 'access_token=%s' % access_token}
        params = {
            'supplierTaxCode': self.supplierTaxCode,
            'transactionUuid': self.transactionID
        }
        try:
            resp = requests.post(url=url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                resp_rslt = json.loads(resp.text).get('result')[0]
                _logger.info('================== VIETTEL SINVOICE: GET INFO BY TRANSACTION ID: %s ' % resp.text)
                if resp_rslt.get('status') == 'Hóa đơn gốc':
                    data = {
                        'supplierTaxCode': resp_rslt['supplierTaxCode'],
                        'name': resp_rslt['invoiceNo'],
                        'invoiceNo': resp_rslt['invoiceNo'],
                        'reservationCode': resp_rslt['reservationCode'],
                        'invoiceIssuedDate': datetime.utcfromtimestamp(resp_rslt.get('issueDate') / 1000),
                        'code_of_tax': resp_rslt.get('codeOfTax'),
                        'state': 'created'
                    }
                    self.write(data)
                elif resp_rslt.get('status') == 'Hóa đơn xóa bỏ':
                    data = {
                        'supplierTaxCode': resp_rslt['supplierTaxCode'],
                        'name': resp_rslt['invoiceNo'],
                        'invoiceNo': resp_rslt['invoiceNo'],
                        'reservationCode': resp_rslt['reservationCode'],
                        'invoiceIssuedDate': datetime.utcfromtimestamp(resp_rslt.get('issueDate') / 1000),
                        'code_of_tax': resp_rslt.get('codeOfTax'),
                        'state': 'canceled',
                        'attachment_ids': [(5, 0, 0)]
                    }
                    self.write(data)
                self.message_post(
                    body='Hóa đơn được kiểm tra trang thái bởi <strong>%s</strong>' % self.env.user.name)
                return True
            else:
                if raise_error:
                    raise UserError('The invoice has not been issued on the Viettel Sinvoice!')
                else:
                    return False
        except Exception as e:
            if raise_error:
                raise UserError('The invoice has not been issued on the Viettel Sinvoice: %s' % e)
            else:
                return False

    # Create invoice
    def action_create_sinvoice(self, draft=False):
        _logger.info('======================= action_create_sinvoice ================')
        # Execute post request to S-Invoice Service to create a new S-Invoice
        self.ensure_one()
        if not self.state == 'confirm':
            raise UserError('Không thể phát hành lại một hóa đơn đã ký!')

        if draft:
            endpoint = self.company_id.vsi_domain + '/InvoiceAPI/InvoiceWS/createOrUpdateInvoiceDraft/' + self.supplierTaxCode
        else:
            endpoint = self.company_id.vsi_domain + '/InvoiceAPI/InvoiceWS/createInvoice/' + self.supplierTaxCode
        if self.adjustmentType == '1':
            data = self._prepare_data_to_send_sinvoice()
        else:
            data = self._prepare_data_to_send_sinvoice_edit()

        access_token = self.company_id.get_access_token()
        headers = {**DEFAULT_HEADER, 'Cookie': 'access_token=%s' % access_token}

        _logger.info('Prepare date for create SInvoice: \n %s' % pprint.pformat(data))
        _logger.info('================== POST DATA TO SINVOICE =================')
        response = requests.post(endpoint, json=data, headers=headers, timeout=10)
        _logger.info('================== STATUS CODE: %s, RESPONSE TEXT: %s' % (response.status_code, response.text))
        self.message_post(body='Hóa đơn đã gửi yêu cầu phát hành bởi <strong>%s</strong>' % self.env.user.name)

        if response.status_code == 200:
            try:
                resp_data = json.loads(response.text)
                if not resp_data.get('errorCode', False) and not resp_data.get('description', False) \
                        and resp_data.get('result', False):
                    rslt = resp_data.get('result', {})
                    self.update_sinvoice_after_send_request(rslt)
                    time.sleep(1)
                    self.action_get_sinvoice_pdf_file()
                    if self.base_sinvoice_id:
                        time.sleep(1)
                        self.base_sinvoice_id.action_get_sinvoice_pdf_file()
                else:
                    raise UserError('Đã xảy ra lỗi !\n %s' % resp_data)
            except Exception as e:
                body = '%s' % e
                self.message_post(body=body)
        else:
            self.message_post(body="Connection errors: %s - %s" % (response.status_code, response.text))
            # raise UserError("Connection errors: %s - %s" % (response.status_code, response.text))
        return True

    # Get invoice PDF file
    def action_get_sinvoice_pdf_file(self):

        url = self.company_id.vsi_domain + '/InvoiceAPI/InvoiceUtilsWS/getInvoiceRepresentationFile'

        data = {
            "supplierTaxCode": self.supplierTaxCode,
            "invoiceNo": self.name,
            "templateCode": self.templateCode,
            "fileType": "PDF",
        }

        access_token = self.company_id.get_access_token()
        headers = {**DEFAULT_HEADER, 'Cookie': 'access_token=%s' % access_token}
        response = requests.post(url, json=data, headers=headers)
        content = response.content
        if content:
            try:
                result = json.loads(content.decode('utf-8'))
                if not result.get('fileToBytes', '').encode():
                    self.message_post(body='File not found!<br> %s' % result)
                else:
                    filename = result.get('fileName', self.name or 'file') + '.pdf'
                    attachment = {
                        'name': filename,
                        'datas': result.get('fileToBytes', '').encode(),
                        'res_model': 'viettel.sinvoice',
                        'res_id': self.id,
                        'type': 'binary',
                    }
                    attachment_id = self.env['ir.attachment'].create(attachment)
                    self.attachment_ids.unlink()
                    self.write({
                        'attachment_ids': [(6, 0, [attachment_id.id])]
                    })
            except Exception as e:
                _logger.info("Exception when execute action_get_sinvoice_pdf_file() %s" % e)
        return True

    # Cancel Invoice
    def action_cancel_sinvoice(self, data={}):

        url = self.company_id.vsi_domain + '/InvoiceAPI/InvoiceWS/cancelTransactionInvoice'

        cancel_data = {
            'supplierTaxCode': self.supplierTaxCode,
            'templateCode': self.templateCode,
            'invoiceNo': self.name,
            'strIssueDate': int(self.invoiceIssuedDate.timestamp()) * 1000,
            'additionalReferenceDesc': data.get('additionalReferenceDesc', ''),
            'additionalReferenceDate': data.get('str_additionalReferenceDate', ''),
            'reasonDelete': data.get('reason', ''),
        }
        access_token = self.company_id.get_access_token()
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        headers = {**headers, 'Cookie': 'access_token=%s' % access_token}

        resp = requests.post(url, params=cancel_data, headers=headers)
        if resp.status_code == 200:
            resp_data = json.loads(resp.text)
            if not resp_data['errorCode'] and resp_data['description'] == 'CANCEL TRANSACTION INVOICE SUCCESS':
                self.write({
                    'state': 'canceled',
                    'cancel_desc': resp_data['description'],
                    'additionalReferenceDesc': data.get('additionalReferenceDesc', ''),
                    'additionalReferenceDate': data.get('additionalReferenceDate', ''),
                    'reason': data.get('reason', ''),
                    'adjustmentType': '7',
                })
                self.action_get_sinvoice_pdf_file()
            else:
                raise UserError('Đã xảy ra lỗi !\n'
                                'errorCode: %s \ndescription : %s' % (
                                    resp_data.get('errorCode'), resp_data.get('description')))
        else:
            raise UserError("Connection errors: %s: %s" % (resp.status_code, resp.text))
        return True

    def action_open_invoice(self):
        self.ensure_one()
        view = self.env.ref('viettel_sinvoice.view_viettel_sinvoice_form')
        return {
            'name': _('S-Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'viettel.sinvoice',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': self.id,
            'context': dict(self.env.context, create=False)
        }
