# -*- coding: utf-8 -*-
import base64
import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MisaInbotDocument(models.Model):
    _name = 'misa.inbot.document'
    _description = 'MISA INBOT Electronic Invoice Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'invoice_date desc, id desc'

    name = fields.Char(string='Document Name', compute='_compute_name', store=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        readonly=False
    )
    move_id = fields.Many2one(
        'account.move',
        string='Account Move',
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
        help='Linked standard Odoo Vendor Bill or Customer Invoice'
    )

    # Identifiers & Basic Inbot Info
    trans_id = fields.Char(string='Transaction ID', index=True, copy=False)
    invoice_id = fields.Char(string='INBOT Invoice ID', index=True, copy=False)
    subscriber_id = fields.Char(string='Subscriber ID', index=True)
    org_id = fields.Char(string='Organization ID', index=True)
    is_inbot = fields.Boolean(
        string='Is Inbound (Input)',
        default=True,
        index=True,
        help='True: Inbound (Vendor Invoice), False: Outbound (Customer Invoice)'
    )
    source_type = fields.Selection([
        ('0', 'CQT (General Department of Taxation)'),
        ('1', 'Uploaded XML by User'),
        ('2', 'Email / Inbot Auto-fetch'),
        ('3', 'Other'),
    ], string='Source Type', default='0', tracking=True)

    # Seller & Buyer Information
    seller_tax_code = fields.Char(string='Seller Tax Code', index=True, tracking=True)
    seller_name = fields.Char(string='Seller Name', tracking=True)
    seller_address = fields.Char(string='Seller Address')

    buyer_tax_code = fields.Char(string='Buyer Tax Code', index=True)
    buyer_name = fields.Char(string='Buyer Name')
    buyer_address = fields.Char(string='Buyer Address')

    # Invoice Template, Series, and Dates
    template_no = fields.Char(string='Template No (Mẫu số)')
    series = fields.Char(string='Invoice Series (Ký hiệu)')
    invoice_no = fields.Char(string='Invoice Number (Số hóa đơn)', index=True, tracking=True)
    invoice_date = fields.Date(string='Invoice Date', index=True, tracking=True)
    issue_date = fields.Date(string='Issue Date')
    mccqt = fields.Char(string='Tax Authority Code (MCCQT)', index=True)
    payment_method = fields.Char(string='Payment Method')
    ccy_code = fields.Char(string='Currency Code', default='VND')
    exchange_rate = fields.Float(string='Exchange Rate', default=1.0, digits=(12, 4))

    # Amounts in Document Currency & Converted Currency (CC)
    total_sale_amount = fields.Monetary(string='Total Sale Amount', currency_field='currency_id')
    total_sale_amount_cc = fields.Monetary(string='Total Sale Amount (VND)')
    total_discount_amount = fields.Monetary(string='Total Discount Amount', currency_field='currency_id')
    total_discount_amount_cc = fields.Monetary(string='Total Discount Amount (VND)')
    total_amount_without_vat = fields.Monetary(string='Total Amount Before VAT', currency_field='currency_id')
    total_amount_without_vat_cc = fields.Monetary(string='Total Amount Before VAT (VND)')
    total_vat_amount = fields.Monetary(string='Total VAT Amount', currency_field='currency_id')
    total_vat_amount_cc = fields.Monetary(string='Total VAT Amount (VND)')
    total_amount = fields.Monetary(string='Total Amount', currency_field='currency_id', tracking=True)
    total_amount_cc = fields.Monetary(string='Total Amount (VND)')
    total_tax_reduction_amount43 = fields.Monetary(
        string='Tax Reduction Amount (Res 43/NQ-QH15)',
        currency_field='currency_id'
    )

    # Decree 70 Fields (Nghị định 70)
    buyer_msdvcqhvns = fields.Char(string='Buyer MSDVCQHVNS')
    seller_msdvcqhvns = fields.Char(string='Seller MSDVCQHVNS')
    buyer_no_citizen_identity_card = fields.Char(string='Buyer CCCD')
    buyer_passport_number = fields.Char(string='Buyer Passport')
    number_agreement = fields.Char(string='Agreement Number')
    agreement_date = fields.Date(string='Agreement Date')
    license_plate = fields.Char(string='License Plate')
    from_location = fields.Char(string='From Location')
    destination = fields.Char(string='Destination')
    is_receipt_decree70 = fields.Boolean(string='Is Receipt Decree 70', default=False)
    is_discount_decree70 = fields.Boolean(string='Is Discount Decree 70', default=False)

    # Checking Result & Tax Risk Flags (CheckingResult)
    seller_risk_status = fields.Selection([
        ('1', '1 - Bình thường (No Risk)'),
        ('2', '2 - Rủi ro danh sách đen thuế (Blacklisted)'),
        ('3', '3 - Chưa đủ thông tin kết luận'),
        ('4', '4 - Ngừng HĐ tại địa chỉ đăng ký (Inactive address)'),
    ], string='Seller Risk Status', default='1', tracking=True, index=True)

    seller_status = fields.Char(string='Seller Tax Status')
    buyer_status = fields.Char(string='Buyer Tax Status')
    published_invoice_status = fields.Char(string='Published Invoice Status')
    seller_signature_status = fields.Char(string='Seller Signature Status')
    taxation_signature = fields.Char(string='Taxation Signature Status')

    # Status Flags & Enums
    invoice_info_status_flags = fields.Char(string='Invoice Info Status Flags')
    checking_status_flags = fields.Char(string='Checking Status Flags')
    t_thai_xu_ly = fields.Selection([
        ('0', 'Chưa xử lý'),
        ('1', 'Đã kiểm tra hợp lệ'),
        ('2', 'Không hợp lệ'),
        ('3', 'Đã hạch toán'),
        ('4', 'Đã thanh toán'),
    ], string='INBOT Processing Status', default='0', tracking=True)

    tinh_chat = fields.Selection([
        ('1', '1 - Hóa đơn Gốc (Original)'),
        ('2', '2 - Hóa đơn Thay thế (Replacement)'),
        ('3', '3 - Hóa đơn Điều chỉnh (Adjustment)'),
        ('4', '4 - Hóa đơn Đã bị thay thế'),
        ('5', '5 - Hóa đơn Đã bị điều chỉnh'),
        ('6', '6 - Hóa đơn Đã bị xóa bỏ / Hủy'),
    ], string='Invoice Nature (Tính chất)', default='1', tracking=True)

    t_thai_hdon = fields.Selection([
        ('1', '1 - Mới lập'),
        ('2', '2 - Đã phát hành'),
        ('3', '3 - Đã gửi CQT'),
        ('4', '4 - CQT tiếp nhận'),
        ('5', '5 - CQT chấp nhận cấp mã'),
        ('6', '6 - CQT không chấp nhận'),
        ('7', '7 - Đã hủy'),
    ], string='Invoice State (CQT)', default='1')

    # Files & Attachments
    xml_file = fields.Binary(string='XML Content File', attachment=True)
    xml_filename = fields.Char(string='XML Filename')
    pdf_file = fields.Binary(string='PDF Preview File', attachment=True)
    pdf_filename = fields.Char(string='PDF Filename')

    # Lines & Related Relations
    line_ids = fields.One2many('misa.inbot.document.line', 'document_id', string='Detail Lines')
    related_line_ids = fields.One2many('misa.inbot.related.line', 'document_id', string='Related Invoices')
    fee_line_ids = fields.One2many('misa.inbot.fee.line', 'document_id', string='Fee Lines')

    _sql_constraints = [
        ('misa_inbot_invoice_unique',
         'unique(company_id, invoice_id, is_inbot)',
         'Invoice ID must be unique per company and direction!'),
    ]

    @api.depends('series', 'invoice_no', 'invoice_date', 'seller_name')
    def _compute_name(self):
        for rec in self:
            prefix = 'IN' if rec.is_inbot else 'OUT'
            num = rec.invoice_no or 'Draft'
            ser = rec.series or ''
            date_str = rec.invoice_date.strftime('%d/%m/%Y') if rec.invoice_date else ''
            partner = (rec.seller_name if rec.is_inbot else rec.buyer_name) or ''
            rec.name = f"[{prefix}] {ser} #{num} ({date_str}) - {partner[:30]}"

    @api.depends('ccy_code')
    def _compute_currency_id(self):
        for rec in self:
            if rec.ccy_code:
                currency = self.env['res.currency'].search([('name', '=ilike', rec.ccy_code.strip())], limit=1)
                rec.currency_id = currency or rec.company_id.currency_id
            else:
                rec.currency_id = rec.company_id.currency_id

    # -------------------------------------------------------------------------
    # Actions: Business Logic & Accounting Bridge
    # -------------------------------------------------------------------------
    def action_create_account_move(self):
        """Create standard Vendor Bill (in_invoice) from INBOT Document with compliance checks."""
        self.ensure_one()
        if self.move_id:
            raise UserError(_("This document is already linked to accounting move %s.") % self.move_id.name)

        if not self.is_inbot:
            raise UserError(_("Automatic account move generation is currently supported for Inbound Vendor Invoices."))

        # Compliance / Risk Gatekeeper Check
        if self.seller_risk_status in ('2', '4'):
            status_label = dict(self._fields['seller_risk_status'].selection).get(self.seller_risk_status)
            raise UserError(_(
                "Cannot generate Vendor Bill: The seller is flagged with high tax risk!\n"
                "Seller: %s (MST: %s)\nRisk Status: %s"
            ) % (self.seller_name, self.seller_tax_code, status_label))

        # 1. Partner Resolution / Creation
        partner = self._find_or_create_partner()

        # 2. Prepare Account Move Lines
        lines = []
        for line in self.line_ids:
            if line.kind == '3':
                # Note / Section line
                lines.append((0, 0, {
                    'display_type': 'line_section',
                    'name': line.item_name or 'Note',
                }))
                continue

            taxes = self._find_tax_for_line(line)
            price_unit = line.unit_price
            qty = line.quantity or 1.0

            line_vals = {
                'name': line.item_name or 'Product/Expense',
                'quantity': qty,
                'price_unit': price_unit,
                'tax_ids': [(6, 0, taxes.ids)],
            }
            if line.discount_amount and line.amount_without_vat:
                # Calculate discount percentage if any
                line_vals['discount'] = round((line.discount_amount / (line.amount_without_vat + line.discount_amount)) * 100, 2)
            lines.append((0, 0, line_vals))

        # Add Fee lines as extra lines if present
        for fee in self.fee_line_ids:
            if fee.fee_amount:
                lines.append((0, 0, {
                    'name': fee.fee_name or 'Fee',
                    'quantity': 1.0,
                    'price_unit': fee.fee_amount,
                }))

        # 3. Create Account Move
        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'ref': self.invoice_no or self.name,
            'invoice_date': self.invoice_date or fields.Date.context_today(self),
            'date': self.invoice_date or fields.Date.context_today(self),
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'misa_inbot_id': self.id,
            'invoice_line_ids': lines,
        }

        move = self.env['account.move'].create(move_vals)
        self.write({
            'move_id': move.id,
            't_thai_xu_ly': '1' if self.t_thai_xu_ly == '0' else self.t_thai_xu_ly,
        })

        # Copy attachments if available
        self._attach_files_to_move(move)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _find_or_create_partner(self):
        """Find partner by VAT/Tax code, or create a new partner if absent."""
        self.ensure_one()
        tax_code = (self.seller_tax_code or '').strip()
        partner_obj = self.env['res.partner']

        partner = False
        if tax_code:
            partner = partner_obj.search([
                '|',
                ('vat', '=', tax_code),
                ('vat', '=', tax_code.replace(' ', ''))
            ], limit=1)

        if not partner and self.seller_name:
            partner = partner_obj.search([
                ('name', '=ilike', self.seller_name.strip()),
                ('is_company', '=', True)
            ], limit=1)

        if not partner:
            partner_vals = {
                'name': self.seller_name or tax_code or _('Unknown Seller'),
                'vat': tax_code,
                'street': self.seller_address or False,
                'is_company': True,
                'supplier_rank': 1,
                'company_id': self.company_id.id,
            }
            partner = partner_obj.create(partner_vals)

        return partner

    def _find_tax_for_line(self, line):
        """Find appropriate purchase tax matching the VAT rate."""
        rate_map = {
            '0': 0.0,
            '5': 5.0,
            '8': 8.0,
            '10': 10.0,
        }
        tax_obj = self.env['account.tax']
        if line.vat_rate in rate_map:
            rate_val = rate_map[line.vat_rate]
            tax = tax_obj.search([
                ('type_tax_use', '=', 'purchase'),
                ('amount_type', '=', 'percent'),
                ('amount', '=', rate_val),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            return tax
        return tax_obj.browse()

    def _attach_files_to_move(self, move):
        """Attach XML and PDF files to the generated account.move."""
        att_obj = self.env['ir.attachment']
        if self.xml_file and self.xml_filename:
            att_obj.create({
                'name': self.xml_filename,
                'type': 'binary',
                'datas': self.xml_file,
                'res_model': 'account.move',
                'res_id': move.id,
                'mimetype': 'application/xml',
            })
        if self.pdf_file and self.pdf_filename:
            att_obj.create({
                'name': self.pdf_filename,
                'type': 'binary',
                'datas': self.pdf_file,
                'res_model': 'account.move',
                'res_id': move.id,
                'mimetype': 'application/pdf',
            })

    # -------------------------------------------------------------------------
    # API 2-Way Sync Triggers: Accounting Date & Payment
    # -------------------------------------------------------------------------
    def action_sync_accounting_date(self, move=None):
        """Push accounting posted date back to MISA INBOT (invoiceaccountingdateV2)."""
        for doc in self:
            if not doc.invoice_id:
                continue
            mv = move or doc.move_id
            subscriber_id = doc.subscriber_id or doc.company_id.misa_inbot_subscribers_id
            org_id = doc.org_id
            if not subscriber_id or not org_id:
                # Try getting from misa.organization
                org = doc.env['misa.organization'].search([('company_id', '=', doc.company_id.id)], limit=1)
                if org:
                    subscriber_id = subscriber_id or org.subscriber_id
                    org_id = org_id or org.org_id

            if not subscriber_id or not org_id:
                _logger.warning("Cannot sync accounting date for document %s: Missing subscriber_id or org_id", doc.name)
                continue

            endpoint = f"meinvoicebot/v1/{subscriber_id}/{org_id}/invoices/invoiceaccountingdateV2"
            accountant_name = self.env.user.name or 'Accountant'
            acc_date = mv.date.strftime('%Y-%m-%d') if (mv and mv.date) else fields.Date.today().strftime('%Y-%m-%d')
            ref_no = mv.name if mv else (doc.invoice_no or '')

            body = {
                'Accountant': accountant_name,
                'AccountingDate': acc_date,
                'InvoiceId': doc.invoice_id,
                'RefNo': ref_no,
            }

            res = doc.company_id._execute_inbot_api(endpoint, method='POST', json_data=body)
            if res.get('is_success'):
                doc.t_thai_xu_ly = '3'
                doc.message_post(body=_("Synchronized accounting date %s with MISA INBOT.") % acc_date)
            else:
                _logger.error("Failed to sync accounting date for INBOT %s: %s", doc.name, res.get('error_message'))

    def action_sync_payment_status(self, move=None):
        """Push payment / reconciliation status back to MISA INBOT (invoicepayment)."""
        for doc in self:
            if not doc.invoice_id:
                continue
            mv = move or doc.move_id
            subscriber_id = doc.subscriber_id or doc.company_id.misa_inbot_subscribers_id
            org_id = doc.org_id
            if not subscriber_id or not org_id:
                org = doc.env['misa.organization'].search([('company_id', '=', doc.company_id.id)], limit=1)
                if org:
                    subscriber_id = subscriber_id or org.subscriber_id
                    org_id = org_id or org.org_id

            if not subscriber_id or not org_id:
                continue

            endpoint = f"meinvoicebot/v1/{subscriber_id}/{org_id}/invoices/invoicepayment"
            payment_date = fields.Date.today().strftime('%Y/%m/%d')
            total_amount = doc.total_amount or (mv.amount_total if mv else 0.0)
            residual = mv.amount_residual if mv else 0.0
            paid_amount = total_amount - residual

            # AmountPayment: 1: Not paid, 2: Fully paid, 5: Partially paid
            if residual == 0.0 and paid_amount > 0:
                amount_payment_code = 2
            elif 0.0 < residual < total_amount:
                amount_payment_code = 5
            else:
                amount_payment_code = 1

            body = {
                'InvoiceId': doc.invoice_id,
                'PaymentDate': payment_date,
                'PaymentPair': paid_amount,
                'TotalAmountPayment': paid_amount,
                'TotalAmountNotPayment': residual,
                'NumberPaymentNext': 0,
                'AmountPayment': amount_payment_code,
            }

            res = doc.company_id._execute_inbot_api(endpoint, method='POST', json_data=body)
            if res.get('is_success'):
                if amount_payment_code == 2:
                    doc.t_thai_xu_ly = '4'
                doc.message_post(body=_("Synchronized payment status to MISA INBOT (Paid: %s, Residual: %s).") % (paid_amount, residual))
            else:
                _logger.error("Failed to sync payment status for INBOT %s: %s", doc.name, res.get('error_message'))
