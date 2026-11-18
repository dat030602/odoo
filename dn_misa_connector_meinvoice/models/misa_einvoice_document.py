# -*- coding: utf-8 -*-
import json
import logging
import uuid
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

REASON_CODE_SELECTION = [
    ('1', '1 - Điều chỉnh giá trị quyết toán dự án đầu tư khi có sự thay đổi về đơn giá, khối lượng; điều chỉnh giá bán theo quy định của pháp luật chuyên ngành'),
    ('2', '2 - Điều chỉnh giá trị, khối lượng trên cơ sở kết luận của cơ quan nhà nước có thẩm quyền'),
    ('3', '3 - Điều chỉnh giá bán buôn điện giữa EVN với các Tổng công ty Điện lực'),
    ('4', '4 - Điều chỉnh do chiết khấu thương mại'),
    ('5', '5 - Điều chỉnh do trả lại hàng hóa không phải là tài sản thuộc diện phải đăng ký quyền sở hữu/sử dụng'),
    ('6', '6 - Thay thế do trả lại hàng hóa là tài sản thuộc diện phải đăng ký quyền sử dụng, quyền sở hữu'),
    ('7', '7 - Điều chỉnh do hoàn phí, giảm phí, giảm hoa hồng môi giới bảo hiểm'),
    ('8', '8 - Điều chỉnh do hủy hoặc chấm dứt giao dịch và hủy một phần việc cung cấp dịch vụ thu tiền trước'),
    ('9', '9 - Điều chỉnh do hoàn phí của tổ chức tín dụng, dịch vụ thanh toán không dùng tiền mặt'),
    ('10', '10 - Điều chỉnh đối với dịch vụ viễn thông sử dụng thẻ trả trước'),
    ('11', '11 - Điều chỉnh do có sự thay đổi về giá trị bán khí thiên nhiên thực tế khi quy đổi VND'),
    ('12', '12 - Điều chỉnh đối với hóa đơn đổi, hoàn chứng từ vận chuyển hàng không'),
    ('13', '13 - Điều chỉnh hoặc thay thế cho hóa đơn đã lập sai'),
    ('14', '14 - Thay thế hóa đơn điện tử đã lập sai khởi tạo từ máy tính tiền (MTT)'),
]


class MisaEinvoiceDocument(models.Model):
    _name = 'misa.einvoice.document'
    _description = 'MISA Decoupled e-Invoice Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inv_date desc, id desc'

    # Identification & State
    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'), index=True)
    ref_id = fields.Char(string='Ref ID (GUID)', required=True, copy=False, index=True, default=lambda self: str(uuid.uuid4()),
                         help='Unique GUID reference sent to MISA for deduplication')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('created', 'XML Created (Unsigned)'),
        ('signed', 'Signed'),
        ('published', 'Published / Effective'),
        ('adjusted', 'Adjusted'),
        ('replaced', 'Replaced'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, index=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)
    exchange_rate = fields.Float(string='Exchange Rate', default=1.0, digits=(12, 4))

    # Thin Links to Odoo Core Models
    move_id = fields.Many2one('account.move', string='Accounting Move / Invoice', ondelete='set null', index=True, copy=False)
    pos_order_id = fields.Many2one('pos.order', string='Point of Sale Order', ondelete='set null', index=True, copy=False)
    picking_id = fields.Many2one('stock.picking', string='Stock Picking (Delivery)', ondelete='set null', index=True, copy=False)
    origin_einvoice_id = fields.Many2one('misa.einvoice.document', string='Original e-Invoice', ondelete='set null', copy=False,
                                         help='Original MISA document being adjusted or replaced')

    # Signing & Template Configuration
    sign_type = fields.Selection([
        ('1', '1 - USB Token / Soft Certificate'),
        ('2', '2 - HSM / Remote eSign'),
        ('5', '5 - POS / Cash Register (MTT)'),
    ], string='Sign Type', default='2', required=True, tracking=True)

    inv_series = fields.Char(string='Invoice Series', required=True, index=True, tracking=True, help='e.g. 1C26TYY, 1C26MYY, 6C26TAA')
    inv_template_no = fields.Char(string='Template Form Number', default='1', required=True)
    inv_no = fields.Char(string='Invoice Number', copy=False, index=True, tracking=True)
    inv_date = fields.Date(string='Invoice Date', default=fields.Date.context_today, required=True, tracking=True)
    payment_method_name = fields.Char(string='Payment Method', default='TM/CK', required=True)

    is_invoice_summary = fields.Boolean(string='Send Summary to Tax Authority', default=False)
    is_send_email = fields.Boolean(string='Send Email Upon Publishing', default=False)
    receiver_name = fields.Char(string='Receiver Name')
    receiver_email = fields.Char(string='Receiver Email', help='Semicolon-separated emails, max 255 chars')

    # Buyer Information
    buyer_code = fields.Char(string='Buyer Code')
    buyer_legal_name = fields.Char(string='Buyer Legal Company Name')
    buyer_tax_code = fields.Char(string='Buyer Tax Code', index=True)
    buyer_address = fields.Char(string='Buyer Address')
    buyer_full_name = fields.Char(string='Buyer Contact Name')
    buyer_phone_number = fields.Char(string='Buyer Phone Number')
    buyer_email = fields.Char(string='Buyer Email')
    buyer_bank_account = fields.Char(string='Buyer Bank Account')
    buyer_bank_name = fields.Char(string='Buyer Bank Name')
    buyer_id_number = fields.Char(string='Buyer Citizen ID / CCCD (12 digits)')
    buyer_passport = fields.Char(string='Buyer Passport (max 20 chars)')
    buyer_budget_code = fields.Char(string='Buyer State Budget Code (Mã ĐVSDNS - 7 chars)')

    # Monetary Total Summary
    total_sale_amount_oc = fields.Monetary(string='Total Sale Amount (OC)', currency_field='currency_id', compute='_compute_totals', store=True)
    total_sale_amount = fields.Monetary(string='Total Sale Amount', currency_field='company_currency_id', compute='_compute_totals', store=True)
    total_discount_amount_oc = fields.Monetary(string='Total Discount (OC)', currency_field='currency_id', compute='_compute_totals', store=True)
    total_discount_amount = fields.Monetary(string='Total Discount', currency_field='company_currency_id', compute='_compute_totals', store=True)
    total_amount_without_vat_oc = fields.Monetary(string='Total Without VAT (OC)', currency_field='currency_id', compute='_compute_totals', store=True)
    total_amount_without_vat = fields.Monetary(string='Total Without VAT', currency_field='company_currency_id', compute='_compute_totals', store=True)
    total_vat_amount_oc = fields.Monetary(string='Total VAT (OC)', currency_field='currency_id', compute='_compute_totals', store=True)
    total_vat_amount = fields.Monetary(string='Total VAT', currency_field='company_currency_id', compute='_compute_totals', store=True)
    total_amount_oc = fields.Monetary(string='Total Amount (OC)', currency_field='currency_id', compute='_compute_totals', store=True)
    total_amount = fields.Monetary(string='Total Amount', currency_field='company_currency_id', compute='_compute_totals', store=True)
    total_amount_in_words = fields.Char(string='Amount in Words')

    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True)

    # Replacement & Adjustment (Circular 91 / Decree 123)
    reference_type = fields.Selection([
        ('0', '0 - Standard Original Invoice (Gốc)'),
        ('1', '1 - Replacement Invoice (Thay thế)'),
        ('2', '2 - Adjustment Invoice (Điều chỉnh)'),
    ], string='Invoice Reference Nature', default='0', required=True, tracking=True)

    org_invoice_type = fields.Selection([
        ('1', '1 - E-Invoice under Decree 123'),
        ('2', '2 - Other / Old system'),
    ], string='Original Invoice Regulation Type', default='1')

    org_inv_template_no = fields.Char(string='Original Template Form No')
    org_inv_series = fields.Char(string='Original Series')
    org_inv_no = fields.Char(string='Original Invoice No')
    org_inv_date = fields.Date(string='Original Invoice Date')
    invoice_note = fields.Text(string='Adjustment / Replacement Note')
    adjust_replace_reason_code = fields.Selection(
        REASON_CODE_SELECTION,
        string='Reason Code (Circular 91 / Appendix XVII)',
        help='Mandatory from Dec 15, 2026 for adjusted or replaced invoices. Maps to <LDDCTThe> in XML.'
    )

    # Technical payloads & URLs
    transaction_id = fields.Char(string='MISA Transaction ID', copy=False, index=True)
    raw_xml = fields.Text(string='Raw Unsigned XML (Token Flow)', copy=False)
    signed_xml = fields.Text(string='Signed XML (Token Flow)', copy=False)
    view_url = fields.Char(string='Preview / View URL', copy=False)
    qr_code_data = fields.Text(string='QR Code Data', copy=False)

    # Stock Delivery Note Fields (Phiếu xuất kho kiêm vận chuyển nội bộ / gửi bán đại lý)
    stock_out_legal_name = fields.Char(string='Dispatch Entity Legal Name (Tên đơn vị xuất)')
    stock_out_tax_code = fields.Char(string='Dispatch Tax Code')
    stock_out_address = fields.Char(string='Dispatch Address')
    stock_out_full_name = fields.Char(string='Dispatcher Person Name')

    internal_command = fields.Char(string='Internal Order / Reason (Lệnh điều động nội bộ)', default='Vận chuyển nội bộ')
    internal_command_no = fields.Char(string='Internal Order No.')
    internal_command_owner = fields.Char(string='Internal Order Issuer (Người ra lệnh)')
    internal_command_date = fields.Date(string='Internal Order Date')

    transporter_name = fields.Char(string='Transporter Name (Họ tên người vận chuyển)')
    transport = fields.Char(string='Transport Means (Phương tiện vận chuyển)')
    transport_contract_code = fields.Char(string='Transport Contract No.')

    stock_in_legal_name = fields.Char(string='Receiving Entity Legal Name (Tên đơn vị nhận)')
    stock_in_tax_code = fields.Char(string='Receiving Tax Code')
    stock_in_full_name = fields.Char(string='Receiver Person Name')
    stock_in_address = fields.Char(string='Receiving Address')

    contract_code = fields.Char(string='Economic Contract No.')
    contract_date = fields.Date(string='Contract Date')
    journal_memo = fields.Char(string='Stock Memo / Reason')
    stock_total_amount_oc = fields.Monetary(string='Stock Total Value (OC)', currency_field='currency_id')
    stock_total_amount = fields.Monetary(string='Stock Total Value', currency_field='company_currency_id')

    # Hospitality / Utilities
    check_in = fields.Datetime(string='Check In Time')
    check_out = fields.Datetime(string='Check Out Time')
    room_no = fields.Char(string='Room / Table No.')
    service_fee_rate = fields.Float(string='Service Fee Rate (%)')
    excise_tax_rate = fields.Float(string='Special Consumption Tax Rate (%)')
    period_name = fields.Char(string='Billing Period (Kỳ tính tiền)')
    old_index = fields.Float(string='Previous Meter Index (Chỉ số cũ)')
    new_index = fields.Float(string='Current Meter Index (Chỉ số mới)')
    clock_infos = fields.Char(string='Meter / Clock Identifiers')

    # Relational lines
    line_ids = fields.One2many('misa.einvoice.document.line', 'document_id', string='Detail Lines', copy=True)
    tax_line_ids = fields.One2many('misa.einvoice.tax.line', 'document_id', string='Tax Summary Lines', copy=True)

    # -------------------------------------------------------------------------
    # Constrains & Computations
    # -------------------------------------------------------------------------
    @api.constrains('buyer_tax_code', 'buyer_budget_code', 'buyer_legal_name', 'buyer_address')
    def _check_buyer_legal_requirements(self):
        for rec in self:
            if rec.buyer_tax_code or rec.buyer_budget_code:
                if not rec.buyer_legal_name or not rec.buyer_address:
                    raise ValidationError(_(
                        "When Buyer Tax Code or Buyer Budget Code is provided, both Buyer Legal Name "
                        "and Buyer Address are strictly required by tax authority regulations."
                    ))

    @api.constrains('reference_type', 'adjust_replace_reason_code')
    def _check_adjust_replace_reason(self):
        for rec in self:
            if rec.reference_type in ['1', '2'] and not rec.adjust_replace_reason_code:
                raise ValidationError(_(
                    "For Replacement (1) or Adjustment (2) invoices, you must specify an Adjust/Replace Reason Code "
                    "according to Circular 91 Appendix XVII."
                ))

    @api.depends('line_ids.amount_oc', 'line_ids.discount_amount_oc',
                 'line_ids.amount_without_vat_oc', 'line_ids.vat_amount_oc',
                 'line_ids.item_type', 'exchange_rate')
    def _compute_totals(self):
        for rec in self:
            rate = rec.exchange_rate or 1.0
            cur = rec.currency_id or rec.env.company.currency_id
            comp_cur = rec.company_currency_id or rec.env.company.currency_id

            sale_oc = 0.0
            disc_oc = 0.0
            without_vat_oc = 0.0
            vat_oc = 0.0

            for line in rec.line_ids:
                if line.item_type in ['1', '2', '5']:
                    sale_oc += line.amount_oc
                    disc_oc += line.discount_amount_oc
                    without_vat_oc += line.amount_without_vat_oc
                    vat_oc += line.vat_amount_oc
                elif line.item_type == '3':  # Commercial discount
                    sale_oc -= line.amount_oc
                    disc_oc += line.amount_oc
                    without_vat_oc -= line.amount_without_vat_oc
                    vat_oc -= line.vat_amount_oc

            rec.total_sale_amount_oc = cur.round(sale_oc)
            rec.total_sale_amount = comp_cur.round(rec.total_sale_amount_oc * rate)

            rec.total_discount_amount_oc = cur.round(disc_oc)
            rec.total_discount_amount = comp_cur.round(rec.total_discount_amount_oc * rate)

            rec.total_amount_without_vat_oc = cur.round(without_vat_oc)
            rec.total_amount_without_vat = comp_cur.round(rec.total_amount_without_vat_oc * rate)

            rec.total_vat_amount_oc = cur.round(vat_oc)
            rec.total_vat_amount = comp_cur.round(rec.total_vat_amount_oc * rate)

            rec.total_amount_oc = cur.round(rec.total_amount_without_vat_oc + rec.total_vat_amount_oc)
            rec.total_amount = comp_cur.round(rec.total_amount_oc * rate)

    @api.onchange('origin_einvoice_id')
    def _onchange_origin_einvoice(self):
        if self.origin_einvoice_id:
            orig = self.origin_einvoice_id
            self.org_invoice_type = '1'
            self.org_inv_no = orig.inv_no
            self.org_inv_date = orig.inv_date
            orig_series = (orig.inv_series or '').strip()
            if orig_series:
                self.org_inv_template_no = orig_series[0]
                self.org_inv_series = orig_series[1:]
            self.buyer_code = orig.buyer_code
            self.buyer_legal_name = orig.buyer_legal_name
            self.buyer_tax_code = orig.buyer_tax_code
            self.buyer_address = orig.buyer_address
            self.buyer_full_name = orig.buyer_full_name
            self.buyer_phone_number = orig.buyer_phone_number
            self.buyer_email = orig.buyer_email

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('misa.einvoice.document') or _('EINV/%s') % fields.Date.today().strftime('%Y%m%d')
            if not vals.get('ref_id'):
                vals['ref_id'] = str(uuid.uuid4())
        docs = super().create(vals_list)
        for doc in docs:
            doc._rebuild_tax_summary()
        return docs

    def write(self, vals):
        res = super().write(vals)
        if 'line_ids' in vals or 'exchange_rate' in vals:
            for rec in self:
                rec._rebuild_tax_summary()
        return res

    def _rebuild_tax_summary(self):
        """Aggregate line items into TaxRateInfo tax_line_ids."""
        self.ensure_one()
        tax_map = {}
        for line in self.line_ids:
            if line.item_type in ['4']:
                continue
            rate_name = line.vat_rate_name or 'KHONGTHUE'
            if rate_name not in tax_map:
                tax_map[rate_name] = {'without_vat_oc': 0.0, 'vat_oc': 0.0}

            factor = -1.0 if line.item_type == '3' else 1.0
            tax_map[rate_name]['without_vat_oc'] += (line.amount_without_vat_oc * factor)
            tax_map[rate_name]['vat_oc'] += (line.vat_amount_oc * factor)

        # Clear old tax lines
        self.tax_line_ids.unlink()

        # Recreate
        cur = self.currency_id or self.company_id.currency_id
        comp_cur = self.company_currency_id or self.company_id.currency_id
        rate = self.exchange_rate or 1.0
        tax_lines_vals = []
        for rate_name, values in tax_map.items():
            w_oc = cur.round(values['without_vat_oc'])
            v_oc = cur.round(values['vat_oc'])
            tax_lines_vals.append((0, 0, {
                'vat_rate_name': rate_name,
                'amount_without_vat_oc': w_oc,
                'amount_without_vat': comp_cur.round(w_oc * rate),
                'vat_amount_oc': v_oc,
                'vat_amount': comp_cur.round(v_oc * rate),
            }))
        if tax_lines_vals:
            self.write({'tax_line_ids': tax_lines_vals})

    # -------------------------------------------------------------------------
    # Payload Builder for meInvoice APIs
    # -------------------------------------------------------------------------
    def _build_misa_invoice_payload(self):
        """Generate InvoiceData dictionary matching MISA OpenAPI specification."""
        self.ensure_one()
        detail_lines = []
        line_no = 1
        for line in self.line_ids:
            sort_val = None if line.item_type in ['3', '4'] else line_no
            detail_lines.append({
                'ItemType': int(line.item_type),
                'SortOrder': sort_val,
                'LineNumber': line_no,
                'ItemCode': line.item_code or '',
                'ItemName': line.item_name or '',
                'UnitName': line.unit_name or '',
                'Quantity': line.quantity,
                'UnitPrice': line.unit_price,
                'AmountOC': line.amount_oc,
                'Amount': line.amount,
                'DiscountRate': line.discount_rate,
                'DiscountAmountOC': line.discount_amount_oc,
                'DiscountAmount': line.discount_amount,
                'AmountWithoutVATOC': line.amount_without_vat_oc,
                'AmountWithoutVAT': line.amount_without_vat,
                'VATRateName': line.vat_rate_name or '',
                'VATAmountOC': line.vat_amount_oc,
                'VATAmount': line.vat_amount,
                'ChassisNumber': line.chassis_number or '',
                'EngineNumber': line.engine_number or '',
                'LicensePlate': line.license_plate or '',
                'LotNo': line.lot_no or '',
                'ExpiryDate': str(line.expiry_date) if line.expiry_date else None,
            })
            line_no += 1

        tax_lines = []
        for tax in self.tax_line_ids:
            tax_lines.append({
                'VATRateName': tax.vat_rate_name,
                'AmountWithoutVATOC': tax.amount_without_vat_oc,
                'AmountWithoutVAT': tax.amount_without_vat,
                'VATAmountOC': tax.vat_amount_oc,
                'VATAmount': tax.vat_amount,
            })

        payload = {
            'RefID': self.ref_id,
            'InvSeries': self.inv_series,
            'InvTemplateNo': self.inv_template_no or '1',
            'InvDate': str(self.inv_date),
            'CurrencyCode': self.currency_id.name or 'VND',
            'ExchangeRate': self.exchange_rate or 1.0,
            'PaymentMethodName': self.payment_method_name or 'TM/CK',
            'IsInvoiceSummary': self.is_invoice_summary,
            'IsSendEmail': self.is_send_email,
            'ReceiverName': self.receiver_name or '',
            'ReceiverEmail': self.receiver_email or '',
            'BuyerCode': self.buyer_code or '',
            'BuyerLegalName': self.buyer_legal_name or '',
            'BuyerTaxCode': (self.buyer_tax_code or '').strip(),
            'BuyerAddress': self.buyer_address or '',
            'BuyerFullName': self.buyer_full_name or '',
            'BuyerPhoneNumber': self.buyer_phone_number or '',
            'BuyerEmail': self.buyer_email or '',
            'BuyerBankAccount': self.buyer_bank_account or '',
            'BuyerBankName': self.buyer_bank_name or '',
            'BuyerIDNumber': self.buyer_id_number or '',
            'BuyerPassport': self.buyer_passport or '',
            'BuyerBudgetCode': self.buyer_budget_code or '',
            'TotalSaleAmountOC': self.total_sale_amount_oc,
            'TotalSaleAmount': self.total_sale_amount,
            'TotalDiscountAmountOC': self.total_discount_amount_oc,
            'TotalDiscountAmount': self.total_discount_amount,
            'TotalAmountWithoutVATOC': self.total_amount_without_vat_oc,
            'TotalAmountWithoutVAT': self.total_amount_without_vat,
            'TotalVATAmountOC': self.total_vat_amount_oc,
            'TotalVATAmount': self.total_vat_amount,
            'TotalAmountOC': self.total_amount_oc,
            'TotalAmount': self.total_amount,
            'TotalAmountInWords': self.total_amount_in_words or '',
            'OriginalInvoiceDetail': detail_lines,
            'TaxRateInfo': tax_lines,
        }

        # Adjustment / Replacement
        if self.reference_type in ['1', '2']:
            payload['ReferenceType'] = int(self.reference_type)
            payload['OrgInvoiceType'] = int(self.org_invoice_type or 1)
            payload['OrgInvTemplateNo'] = self.org_inv_template_no or ''
            payload['OrgInvSeries'] = self.org_inv_series or ''
            payload['OrgInvNo'] = self.org_inv_no or ''
            payload['OrgInvDate'] = str(self.org_inv_date) if self.org_inv_date else None
            payload['InvoiceNote'] = self.invoice_note or ''
            if self.adjust_replace_reason_code:
                payload['AdjustReplaceReasonCode'] = int(self.adjust_replace_reason_code)

        # Stock Delivery Note Fields (PXK)
        if (self.inv_series or '').startswith('6') or self.picking_id:
            payload.update({
                'StockOutLegalName': self.stock_out_legal_name or self.company_id.name,
                'StockOutTaxCode': self.stock_out_tax_code or self.company_id.misa_tax_code,
                'StockOutAddress': self.stock_out_address or self.company_id.partner_id.contact_address,
                'StockOutFullName': self.stock_out_full_name or '',
                'InternalCommand': self.internal_command or '',
                'InternalCommandNo': self.internal_command_no or '',
                'InternalCommandOwner': self.internal_command_owner or '',
                'InternalCommandDate': str(self.internal_command_date) if self.internal_command_date else None,
                'TransporterName': self.transporter_name or '',
                'Transport': self.transport or '',
                'TransportContractCode': self.transport_contract_code or '',
                'StockInLegalName': self.stock_in_legal_name or '',
                'StockInTaxCode': self.stock_in_tax_code or '',
                'StockInFullName': self.stock_in_full_name or '',
                'StockInAddress': self.stock_in_address or '',
                'ContractCode': self.contract_code or '',
                'ContractDate': str(self.contract_date) if self.contract_date else None,
                'JournalMemo': self.journal_memo or '',
                'StockTotalAmountOC': self.stock_total_amount_oc or self.total_amount_oc,
                'StockTotalAmount': self.stock_total_amount or self.total_amount,
            })

        # Hospitality / Utilities
        if self.room_no or self.check_in:
            payload.update({
                'CheckIn': self.check_in.strftime('%Y-%m-%d %H:%M:%S') if self.check_in else None,
                'CheckOut': self.check_out.strftime('%Y-%m-%d %H:%M:%S') if self.check_out else None,
                'RoomNo': self.room_no or '',
                'ServiceFeeRate': self.service_fee_rate or 0.0,
                'ExciseTaxRate': self.excise_tax_rate or 0.0,
            })
        if self.period_name or self.old_index:
            payload.update({
                'PeriodName': self.period_name or '',
                'OldIndex': self.old_index or 0.0,
                'NewIndex': self.new_index or 0.0,
                'ClockInfos': self.clock_infos or '',
            })

        return payload

    # -------------------------------------------------------------------------
    # Actions: Issuance / Publishing
    # -------------------------------------------------------------------------
    def action_publish_hsm(self):
        """Flow 1: Publish with HSM / Cloud eSign (SignType 2) or POS (SignType 5)."""
        self.ensure_one()
        if self.state not in ['draft', 'created']:
            raise UserError(_("Document %s is already %s.") % (self.name, self.state))

        # Check HSM certificates if sign_type == 2
        if self.sign_type == '2':
            certs = self.env['misa.certificate'].search([
                ('company_id', '=', self.company_id.id),
                ('sign_type', '=', '2'),
                ('is_active_cert', '=', True)
            ])
            if not certs:
                # Attempt to sync once
                self.env['misa.certificate'].sync_certificates(self.company_id.id)
                certs = self.env['misa.certificate'].search([
                    ('company_id', '=', self.company_id.id),
                    ('sign_type', '=', '2'),
                    ('is_active_cert', '=', True)
                ])
                if not certs:
                    raise UserError(_(
                        "No active HSM or remote digital certificate found for company %s. "
                        "SignType 2 requires a valid HSM certificate."
                    ) % self.company_id.name)

        token = self.company_id.action_get_meinvoice_token()
        headers = {
            'ClientID': self.company_id.misa_client_id,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        body = {
            'SignType': int(self.sign_type),
            'InvoiceData': [self._build_misa_invoice_payload()],
        }

        res = self.company_id._misa_request(
            service_type='meinvoice',
            endpoint='invoice/publishing',
            method='POST',
            headers=headers,
            json_data=body,
        )

        if not res['is_success']:
            raise UserError(_("Publishing failed: %s (%s)") % (res['error_message'], res['error_code']))

        res_data = res.get('data') or {}
        publish_results = res_data.get('publishInvoiceResult') or []
        if isinstance(publish_results, list) and publish_results:
            p_res = publish_results[0]
            err = p_res.get('ErrorCode')
            if err:
                raise UserError(_("MISA publishing returned error: %s - %s") % (err, p_res.get('DescriptionErrorCode') or p_res.get('Error')))

            inv_no = p_res.get('InvNo')
            trans_id = p_res.get('TransactionID')
            inv_date = p_res.get('InvDate')

            vals = {
                'state': 'published',
                'inv_no': inv_no or self.inv_no,
                'transaction_id': trans_id or self.transaction_id,
            }
            if inv_date:
                try:
                    vals['inv_date'] = datetime.strptime(inv_date[:10], '%Y-%m-%d').date()
                except Exception:
                    pass
            self.write(vals)
            self.message_post(body=_("Published successfully on MISA meInvoice. InvNo: %s, TransactionID: %s") % (inv_no, trans_id))
        else:
            self.write({'state': 'published'})
            self.message_post(body=_("Published successfully on MISA meInvoice."))

        return True

    def action_create_raw_xml(self):
        """Flow 2, Step 1: Create unsigned raw XML for USB Token flow (SignType 1)."""
        self.ensure_one()
        token = self.company_id.action_get_meinvoice_token()
        headers = {
            'ClientID': self.company_id.misa_client_id,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        body = {
            'SignType': 1,
            'InvoiceData': [self._build_misa_invoice_payload()],
            'PublishInvoiceData': None,
        }

        res = self.company_id._misa_request(
            service_type='meinvoice',
            endpoint='invoice/publishing/token',
            method='POST',
            headers=headers,
            json_data=body,
        )

        if not res['is_success']:
            raise UserError(_("Failed to generate raw XML: %s (%s)") % (res['error_message'], res['error_code']))

        res_data = res.get('data') or {}
        create_results = res_data.get('createInvoiceResult') or []
        raw_xml_text = None
        trans_id = None
        if isinstance(create_results, list) and create_results:
            first = create_results[0]
            raw_xml_text = first.get('InvoiceData') or first.get('rawXML') or first.get('XMLData')
            trans_id = first.get('TransactionID')

        self.write({
            'state': 'created',
            'raw_xml': raw_xml_text or json.dumps(create_results, ensure_ascii=False),
            'transaction_id': trans_id or self.transaction_id,
        })
        self.message_post(body=_("Raw XML generated for USB Token signing. TransactionID: %s") % (trans_id or 'N/A'))
        return True

    def action_publish_signed_xml(self):
        """Flow 2, Step 3: Publish signed XML to MISA Cloud (SignType 1)."""
        self.ensure_one()
        if not self.signed_xml:
            raise UserError(_("No signed XML found! Please sign the raw XML with your USB Token tool first."))

        token = self.company_id.action_get_meinvoice_token()
        headers = {
            'ClientID': self.company_id.misa_client_id,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        body = {
            'SignType': 1,
            'InvoiceData': None,
            'PublishInvoiceData': [{
                'RefID': self.ref_id,
                'TransactionID': self.transaction_id or '',
                'InvSeries': self.inv_series,
                'InvoiceData': self.signed_xml,
            }],
        }

        res = self.company_id._misa_request(
            service_type='meinvoice',
            endpoint='invoice/publishing/token',
            method='POST',
            headers=headers,
            json_data=body,
        )

        if not res['is_success']:
            raise UserError(_("Failed to publish signed XML: %s (%s)") % (res['error_message'], res['error_code']))

        res_data = res.get('data') or {}
        pub_results = res_data.get('publishInvoiceResult') or []
        inv_no = None
        trans_id = None
        if isinstance(pub_results, list) and pub_results:
            p_res = pub_results[0]
            err = p_res.get('ErrorCode')
            if err:
                raise UserError(_("MISA publishing returned error: %s - %s") % (err, p_res.get('DescriptionErrorCode') or p_res.get('Error')))
            inv_no = p_res.get('InvNo')
            trans_id = p_res.get('TransactionID')

        self.write({
            'state': 'published',
            'inv_no': inv_no or self.inv_no,
            'transaction_id': trans_id or self.transaction_id,
        })
        self.message_post(body=_("Published signed XML successfully. InvNo: %s, TransactionID: %s") % (inv_no, trans_id))
        return True

    def action_get_preview_url(self):
        """Request 5-minute unpublish view URL and open preview wizard."""
        self.ensure_one()
        token = self.company_id.action_get_meinvoice_token(is_draft=True)
        headers = {
            'ClientID': self.company_id.misa_client_id,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        body = self._build_misa_invoice_payload()

        res = self.company_id._misa_request(
            service_type='meinvoice',
            endpoint='invoice/unpublishview',
            method='POST',
            headers=headers,
            json_data=body,
        )

        if not res['is_success']:
            raise UserError(_("Failed to generate preview URL: %s (%s)") % (res['error_message'], res['error_code']))

        res_data = res.get('data') or {}
        preview_url = ''
        if isinstance(res_data, dict):
            preview_url = res_data.get('Data') or res_data.get('data') or res_data.get('url') or ''
        elif isinstance(res_data, str) and (res_data.startswith('http://') or res_data.startswith('https://')):
            preview_url = res_data

        if not preview_url:
            raise UserError(_("No preview URL returned by MISA: %s") % res_data)

        self.view_url = preview_url

        # Return action opening the preview wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('e-Invoice Preview'),
            'res_model': 'misa.einvoice.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_preview_url': preview_url,
            },
        }

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == 'published':
                raise UserError(_("Cannot reset a published e-Invoice back to draft! Please issue an adjustment or replacement instead."))
            rec.state = 'draft'
