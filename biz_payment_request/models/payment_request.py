# -*- coding: utf-8 -*-

from cryptography.hazmat.primitives import serialization
import json
import urllib.error
import urllib.request
import base64
import logging
import unicodedata
import os
import http.client
from odoo import api, fields, models, _
from odoo.modules.module import get_module_resource
from datetime import datetime, timezone, timedelta
from odoo.exceptions import UserError, ValidationError

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    hashes = serialization = padding = None

_logger = logging.getLogger(__name__)

class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _description = 'Payment Request'

    bank_api_url = 'https://api.vietinbank.vn/vtb/public/erp/v1/payment/transfer'
    #bank_api_url_tk_name = 'https://api-uat.vietinbank.vn/vtb-api-uat/development/erp/v1/account/benAcctInq'
    bank_api_url_tk_name = 'https://api.vietinbank.vn/vtb/public/erp/v1/account/benAcctInq'
    name = fields.Char(string="Name")
    date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self), string="Date")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string="Company")
    company_currency_id = fields.Many2one('res.currency', default=23, store=True, readonly=False, string="Currency")
    total_amount = fields.Monetary(string="Total Amount", readonly=False, currency_field='currency_id', help="Total amount impacted by the automatic entry.")
    
    currency_name = fields.Char(related='currency_id.name', string='Currency Name')
    fcurrency_rate = fields.Float(string="Tỷ giá áp dụng", compute="_compute_fcurrency_rate", store=True, readonly=False)
    vnd_value = fields.Monetary(string="Số tiền quy đổi ra VND", compute="_compute_vnd_value", store=True, currency_field='company_currency_id')

    @api.depends('currency_id', 'date')
    def _compute_fcurrency_rate(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.name != 'VND':
                rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', rec.currency_id.id),
                    ('name', '<=', rec.date or fields.Date.context_today(self))
                ], order='name desc', limit=1)
                rec.fcurrency_rate = rate.inverse_company_rate if rate else 1.0
            else:
                rec.fcurrency_rate = 1.0

    @api.depends('total_amount', 'fcurrency_rate')
    def _compute_vnd_value(self):
        for rec in self:
            rec.vnd_value = rec.total_amount * rec.fcurrency_rate

    fixed_sender_tk = fields.Many2one('res.partner.bank', string="Tài khoản gửi", default=lambda self: self.env['res.partner.bank'].search([('acc_number', '=', '110002630105')], limit=1))
    fixed_sender_tk_name = fields.Char(string="Tên người gửi", default='CTY TNHH CON CO VANG')

    journal_id = fields.Many2one('account.journal', string="Journal",
        domain="[('company_id', '=', company_id)]",
        compute="_compute_journal_id",
        inverse="_inverse_journal_id",
        help="Journal where to create the entry.", store=True, readonly=False)
    account_id = fields.Many2one(string="Account From", comodel_name='account.account',
                                             help="Account to transfer to.")
    destination_account_id = fields.Many2one(string="Account To", comodel_name='account.account', help="Account to receive.")
    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", string="Partner", related="user_id.partner_id", store=True)
    move_id = fields.Many2one("account.move", string="Invoice")
    count_invoice = fields.Integer(string="Count Invoice", default=1, compute="compute_count_invoice")
    def compute_count_invoice(self):
        for res in self:
            count_invoice = 0
            invoices = self.env['account.move'].search([('payment_request_id', '=', res.id)])
            if invoices:
                count_invoice = len(invoices)
            res.count_invoice = count_invoice
            
    count_payment = fields.Integer(string="Count Payment", default=1, compute="compute_count_payment")
    
    def compute_count_payment(self):
        for res in self:
            count_payment = 0
            payments = self.env['account.payment'].search([('payment_request_id', '=', res.id)])
            if payments:
                count_payment = len(payments)
            res.count_payment = count_payment
            
    state = fields.Selection(
        [('draft', 'Draft'), ('approve', 'Approve'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancel'), ('refuse', 'Refuse'),], 'State', default="draft", tracking=True)
    note = fields.Char("Note")
    note_chuyen_khoan = fields.Char("Nội dung Chuyển khoản")

    @api.onchange('note', 'type')
    def _onchange_note_to_chuyen_khoan(self):
        for rec in self:
            if rec.type == 'transfer' and rec.note:
                rec.note_chuyen_khoan = rec.note
    trp_approve_history_ids = fields.One2many('trp.approve.history', 'payment_request_id', string='Trp Approve History', copy=False)
    
    partner_bank_id = fields.Many2one('res.partner.bank', string="Bank account")
    partner_napas_code = fields.Char(string="Napas Code", compute="_compute_partner_napas_code", store=True, readonly=False)
    partner_tk_name = fields.Char(string="Chủ số tài khoản thụ hưởng (Ngân hàng)")
    
    @api.onchange('partner_bank_id', 'partner_napas_code')
    def _onchange_partner_tk_name(self):
        for rec in self:
            if rec.partner_bank_id:
                if not rec.partner_napas_code or len(rec.partner_napas_code) < 4:
                    rec.partner_tk_name = ''
                    return {
                        'warning': {
                            'title': 'VietinBank Warning', 
                            'message': 'Vui lòng nhập Napas Code'
                        }
                    }
                try:
                    payload_tk_name, data_to_sign_tk_name = rec._build_bank_payload_get_tk_name()
                    status_code_tk_name, account_name_tk_name, error_detail = rec._send_bank_request_tk_name(payload_tk_name, data_to_sign_tk_name)
                    if str(status_code_tk_name).strip() == "1" and account_name_tk_name:
                        rec.partner_tk_name = account_name_tk_name
                    else:
                        rec.partner_tk_name = ''
                        return {
                            'warning': {
                                'title': 'VietinBank Warning', 
                                'message': 'Không tìm thấy tên chủ tài khoản! Vui lòng kiểm tra lại Số tài khoản hoặc Napas Code.'
                            }
                        }
                except Exception as e:
                    rec.partner_tk_name = ''
                    # Xử lý ValidationError hoặc Exception khác và ném ra popup cho người dùng
                    error_msg = getattr(e, 'name', str(e))
                    return {
                        'warning': {
                            'title': 'Lỗi kết nối VietinBank', 
                            'message': error_msg
                        }
                    }
            else:
                rec.partner_tk_name = ''
    
    def action_bank_transfer_tk_name(self):
        for rec in self:
            if rec.partner_bank_id:
                if rec.partner_bank_id.bank_id and hasattr(rec.partner_bank_id.bank_id, 'napas_code'):
                    rec.partner_napas_code = rec.partner_bank_id.bank_id.napas_code
                    
                if not rec.partner_napas_code or len(rec.partner_napas_code) < 4:
                    raise ValidationError(_('Vui lòng nhập Napas Code'))
                try:
                    payload_tk_name, data_to_sign_tk_name = rec._build_bank_payload_get_tk_name()
                    status_code_tk_name, account_name_tk_name, error_detail = rec._send_bank_request_tk_name(payload_tk_name, data_to_sign_tk_name)
                    if str(status_code_tk_name).strip() == "1" and account_name_tk_name:
                        rec.partner_tk_name = account_name_tk_name
                    else:
                        rec.partner_tk_name = ''
                        detail_msg = '\nChi tiết: %s' % error_detail if error_detail else ''
                        raise ValidationError(_('Không tìm thấy tên chủ tài khoản! Vui lòng kiểm tra lại Số tài khoản hoặc Napas Code (đang dùng: %s).%s') % (rec.partner_napas_code, detail_msg))
                except ValidationError:
                    raise
                except Exception as e:
                    rec.partner_tk_name = ''                 
                    error_msg = getattr(e, 'name', str(e))
                    raise ValidationError(_(error_msg))
            else:
                rec.partner_tk_name = ''
                raise ValidationError(_('Vui lòng chọn tài khoản ngân hàng'))

    @api.depends('partner_bank_id')
    def _compute_partner_napas_code(self):
        for rec in self:
            if rec.partner_bank_id and rec.partner_bank_id.bank_id and hasattr(rec.partner_bank_id.bank_id, 'napas_code'):
                rec.partner_napas_code = rec.partner_bank_id.bank_id.napas_code
            else:
                rec.partner_napas_code = False
    partner_name = fields.Char(string="Người thụ hưởng (Odoo)", compute="_compute_partner_name", store=True, readonly=False)
    type = fields.Selection([('transfer', 'Transfer'), ('cash', 'Cash'), ('disbursement', 'Giải ngân')], string="Payment Type", default="transfer")
    invoice_name = fields.Char(string="Hóa đơn")
    payment_date = fields.Date(string="Ngày thanh toán")
    
    payment_note_ids = fields.One2many('payment.product.note','payment_request_id')
    amount_untax_total = fields.Monetary("Tổng chưa thuế (VND)", compute="_compute_total_amounts", store=True, currency_field='company_currency_id')
    amount_tax_total = fields.Monetary("Tổng thuế (VND)", compute="_compute_total_amounts", store=True, currency_field='company_currency_id')
    amount_total = fields.Monetary("Tổng cộng (VND)", compute="_compute_total_amounts", store=True, currency_field='company_currency_id')
    famount_total = fields.Monetary("Tổng Ngoại tệ", compute="_compute_total_amounts", store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id.id)
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)

    @api.depends('payment_note_ids.amount_untax', 'payment_note_ids.amount_tax', 'payment_note_ids.fcurrent_amount', 'payment_note_ids.amount_total', 'payment_note_ids.quantity', 'payment_note_ids.fprice_unit', 'payment_note_ids.fcurrency_rate', 'payment_note_ids.tax_id', 'payment_note_ids.famount_untax', 'payment_note_ids.famount_tax', 'currency_id')
    def _compute_total_amounts(self):
        for rec in self.sudo():
            rec.amount_untax_total = sum(rec.payment_note_ids.mapped('amount_total'))
            rec.amount_tax_total = sum(rec.payment_note_ids.mapped('amount_tax'))
            rec.amount_total = rec.amount_tax_total + rec.amount_untax_total
            
            fcurrent_total = sum(rec.payment_note_ids.mapped('fcurrent_amount'))
            is_vnd = rec.currency_id.name == 'VND' or (rec.currency_id.currency_unit_label and str(rec.currency_id.currency_unit_label).lower() == 'vnd')
            if not is_vnd:
                rec.famount_total = fcurrent_total
                rec.total_amount = rec.famount_total
            else:
                rec.famount_total = 0.0
                rec.total_amount = rec.amount_total

    @api.depends_context('lang')
    @api.depends('payment_note_ids.tax_id', 'payment_note_ids.price_unit', 'amount_total', 'amount_untax_total', 'currency_id')
    def _compute_tax_totals(self):
        for rec in self:
            lines = rec.payment_note_ids
            rec.tax_totals = rec.env['account.tax'].sudo()._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in lines],
                rec.currency_id or rec.company_id.currency_id,
            )
    
    @api.depends('partner_bank_id')
    def _compute_partner_name(self):
        for rec in self:
            if rec.partner_bank_id:
                rec.partner_name = rec.partner_bank_id.acc_holder_name

    @api.onchange('type')
    def onchange_type(self):
        if self.type == 'cash':
            self.partner_bank_id = False

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            seq_date = None
            vals_list['name'] = self.env['ir.sequence'].next_by_code('payment.request', sequence_date=seq_date) or 'New'
        return super(PaymentRequest, self).create(vals_list)
    
    def unlink(self):
        for record in self:
            if record.state in ['approve', 'cancel']:
                record.state = 'draft'
        return super(PaymentRequest, self).unlink()

    @api.depends('company_id')
    def _compute_journal_id(self):
        for record in self:
            record.journal_id = record.company_id.automatic_entry_default_journal_id

    def action_create_line(self):
        vals = []
        balance = self.company_currency_id._convert(self.total_amount, self.company_id.currency_id, self.company_id, fields.Date.today())
        vals.append((0, 0, {
            'name': self.note,
            'debit': balance,
            'credit': 0,
            'account_id': self.account_id.id,
            'partner_id': self.user_id.partner_id.id,
            'amount_currency': self.total_amount,
            'currency_id': self.company_currency_id.id,
            'analytic_distribution': False,
        }))
        vals.append((0, 0, {
             'name': self.note,
             'debit': 0,
             'credit': balance,
             'account_id': self.destination_account_id.id,
             'partner_id': self.user_id.partner_id.id,
             'currency_id': self.company_currency_id.id,
             'amount_currency': - self.total_amount
        }))
        return vals
    
    def _inverse_journal_id(self):
        for record in self:
            record.company_id.sudo().automatic_entry_default_journal_id = record.journal_id

    
    def _build_bank_payload(self):
        self.ensure_one()

        key_path_check = get_module_resource('biz_payment_request', 'security', 'private_key.pem')
        if not key_path_check:
            _logger.error("Private key file not found in security folder.") 
            raise ValidationError(_('Private key file not found in security folder.'))

        if not self.partner_bank_id:
            raise ValidationError(_('Chưa chọn tài khoản đối tác nhận tiền.'))

        
        if self.total_amount <= 0:
            raise ValidationError(_('Tổng tiền phải lớn hơn 0.'))
        total_amount_input = str(int(self.total_amount))
        


        sender_account_input = self.fixed_sender_tk.acc_number if self.fixed_sender_tk else '110002630105'
        sender_name_input = self.fixed_sender_tk_name if self.fixed_sender_tk_name else 'CTY TNHH CON CO VANG'
        vietinbank_napas_bank_code ="970415"
        vietinbank_in_bank_code ="01201001"


        beneficiary_account_input = self.partner_bank_id.acc_number
        if not beneficiary_account_input or len(beneficiary_account_input) < 4 or str(beneficiary_account_input).strip() == str(sender_account_input).strip():
            raise ValidationError(_('Số tài khoản thụ hưởng không hơp lệ'))
  
        beneficiary_name_input = self._remove_vietnamese_accents(self.partner_tk_name)
        if not beneficiary_name_input or len(beneficiary_name_input) < 3:
            raise ValidationError(_('Tên thụ hưởng không hợp lệ'))
   
        beneficiary_bank_code_input = self.partner_napas_code
        if not beneficiary_bank_code_input or len(beneficiary_bank_code_input) < 4:
            raise ValidationError(_('Mã ngân hàng thụ hưởng không hợp lệ')) 
 
        message_transfer = self._remove_vietnamese_accents(self.note_chuyen_khoan)
        public_ip = None        
        with urllib.request.urlopen("https://api.ipify.org") as response:
            public_ip = response.read().decode("utf-8")

        transType = "np"
        if (beneficiary_bank_code_input == vietinbank_napas_bank_code):
            transType = "in"
            beneficiary_bank_code_input = vietinbank_in_bank_code
        
        gmt7 = timezone(timedelta(hours=7))
        now_gmt7 = datetime.now(gmt7)

        payload = { 
            
            "requestId": "request" + datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3], #tu tao
            "merchantId": "",
            "providerId": "CONCOVANG",  #ngan hàng setup
            "model": "2",
            "softwareProviderId": "ERP-CCV", 
            #"totalAmount":"150000",# check delete         
            "priority": "3",   
            #"feeAccount": "112000104547",
            "feeAccount": sender_account_input,
            "feeType": "BEN",
            "appointedApprover": "ketoanccv",  #ngan hàng setup
            "scheduledDate": "",
            "approver": "300126682maidan.hoang", #ngan hàng setup
            "records": [ 
                { 
                    "transId": "ccv" + datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3], #tụ tọa lenght <=30 "(-----1)"
                    "approver": "300126682maidan.hoang", #ngan hàng setup               
                    "transType": transType,                     
                    "amount": total_amount_input,
                    "recvAcctId": beneficiary_account_input,                                                   #(------3)
                    "recvBankId": beneficiary_bank_code_input, #ngan hàng cung cap
                    "recvBranchId": beneficiary_bank_code_input, #ngan hàng cung cap --để trống hoặc lây giông bankId được
                    "recvBankName": beneficiary_bank_code_input, 
                    "recvAcctName": beneficiary_name_input,
                    "recvAddr": "", 
                    "remark": message_transfer,  
                    "currencyCode": "VND",         
                    "senderBankId": vietinbank_in_bank_code, #ngan hàng cung cap
                    "senderBranchId": vietinbank_in_bank_code, #ngan hàng cung cap --để trống hoặc lây giông bankId được
                    "senderAcctId": sender_account_input,
                    "senderAcctName": sender_name_input, 
                    "senderAddr": "CN NAM SAI GON - HOI SO", 
                } 
            ], 
            "channel":"WEB",
            "version":"1.0",  
            "clientIP":public_ip,     
            "language":"vi",
            "transTime":now_gmt7.strftime('%Y%m%d%H%M%S'), #real time gmt+7
            }

        ordered_keys = [            
            "requestId",
            "providerId",
            "merchantId",
            "model",
            "priority",
            "softwareProviderId",
            "appointedApprover",
            "feeAccount",
            "feeType", 
            "scheduledDate",
            "approver"
        ]
        record_keys = [
            "transId",
            "senderAcctId",
            "recvAcctId",
            "amount"
        ]
        tail_keys = [
            "transTime",
            "channel",
            "version",
            "clientIP",           
            "language"
        ]
        
        # Create Digital Signature      
        signature_data = []
        # header
        for key in ordered_keys:
            value = payload.get(key)
            if value is not None and value != "":
                signature_data.append(str(value))

                # records
        for record in payload.get("records", []):
            for key in record_keys:
                value = record.get(key)
                if value is not None and value != "":
                    signature_data.append(str(value))
        # tail
        for key in tail_keys:
            value = payload.get(key)
            if value is not None and value != "":
                signature_data.append(str(value))      
                    
        data_to_sign = ''.join(signature_data)
        signature = self._generate_signature(data_to_sign)
        if signature:
            payload['signature'] = signature

        return json.dumps(payload, ensure_ascii=False), data_to_sign

    def _build_bank_payload_get_tk_name(self):
        self.ensure_one()

        key_path_check = get_module_resource('biz_payment_request', 'security', 'private_key.pem')
        if not key_path_check:
            _logger.error("Private key file not found in security folder.") 
            raise ValidationError(_('Private key file not found in security folder.'))

        if not self.partner_bank_id:
            raise ValidationError(_('Chưa chọn tài khoản đối tác nhận tiền.'))

        beneficiary_account_input = self.partner_bank_id.acc_number
        if not beneficiary_account_input or len(beneficiary_account_input) < 4:
            raise ValidationError(_('Số tài khoản thụ hưởng không hơp lệ'))
   
        beneficiary_bank_code_input = self.partner_napas_code
        if not beneficiary_bank_code_input or len(beneficiary_bank_code_input) < 4:
            raise ValidationError(_('Mã ngân hàng thụ hưởng không hợp lệ'))
        # if (beneficiary_bank_code_input.strip() == '01201001'):
        #     beneficiary_bank_code_input = "970415"

        public_ip = None        
        with urllib.request.urlopen("https://api.ipify.org") as response:
            public_ip = response.read().decode("utf-8")
        
        gmt7 = timezone(timedelta(hours=7))
        now_gmt7 = datetime.now(gmt7)

        payload = { 
            
            "requestId": "requesttk" + datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3], #tu tao
            "merchantId": "",
            "providerId": "CONCOVANG",  #ngan hàng setup
            "account": beneficiary_account_input,
            "bankId": beneficiary_bank_code_input,
            "version":"1.0",
            "clientIP":public_ip,
            "channel":"WEB",
            "language":"vi",
            "transTime":now_gmt7.strftime('%Y%m%d%H%M%S')
            }

        ordered_keys = [            
            "requestId",
            "providerId",
            "merchantId",
            "account",
            "bankId",
            "clientIP",
            "channel",
            "version",
            "language"
        ]   
        
        # Create Digital Signature      
        signature_data = []
        # header
        for key in ordered_keys:
            value = payload.get(key)
            if value is not None and value != "":
                signature_data.append(str(value))             
                    
        data_to_sign = ''.join(signature_data)
        signature = self._generate_signature(data_to_sign)
        if signature:
            payload['signature'] = signature

        return json.dumps(payload, ensure_ascii=False), data_to_sign
    
    def _remove_vietnamese_accents(self, text):
        if not text:
            return ''
        # Chuẩn hóa unicode
        text = unicodedata.normalize('NFD', text)
        
        # Loại bỏ dấu
        text = ''.join(
            char for char in text
            if unicodedata.category(char) != 'Mn'
        )
        
        # Xử lý riêng đ/Đ
        text = text.replace('đ', 'd').replace('Đ', 'D')

        text = text.replace('(', '').replace(')', '')
        
        return text

    def _generate_signature(self, data):
        """ Generate RSA-SHA256 signature using private key """
        if not hashes:
            _logger.error("Cryptography library not installed.")
            return False
        
        key_path = get_module_resource('biz_payment_request', 'security', 'private_key.pem')
        if not key_path:
            _logger.error("Private key file not found in security folder.")
            return False

        try:
            with open(key_path, 'rb') as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=b'@ccv123456',
                )
                
            signature = private_key.sign(
                data.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            _logger.error("Failed to generate signature: %s", str(e))
            return False

    def _send_bank_request(self, payload, data_to_sign):
        self.ensure_one()

        if self.currency_id.name.lower() != 'vnd':
            raise ValidationError(_('Chỉ hỗ trợ thanh toán bằng VND.'))

        if not self.bank_api_url:
            raise ValidationError(_('URL API VietinBank chưa được cấu hình.'))

        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'x-ibm-client-id': '6181ed54f6545743a5c6eb94762ae309',
            'x-ibm-client-secret': '9bf59095a68635448a87263a7c303281',
            'Accept': 'application/json'
        }
        request = urllib.request.Request(
            self.bank_api_url,
            data=payload.encode('utf-8'),
            headers=headers,
            method='POST',
        )
        try:
            response = urllib.request.urlopen(request, timeout=60)
            body = response.read().decode('utf-8')            
            data = json.loads(body)
            status_code = data.get("status", {}).get("code") 
            if str(status_code) != "1":
                raise ValidationError(_('Lỗi khi gửi yêu cầu tới VietinBank status: code:  %s\n body: %s\n data_to_sign_check: %s\n payload: %s') % (status_code, body, data_to_sign, payload))
            else:
                for rec in self:
                    if rec.state == 'approved' and rec.type == 'transfer':
                        rec.write({'state': 'done'})
                return status_code, body
        except urllib.error.HTTPError as error:
            body = error.read().decode('utf-8') if hasattr(error, 'read') else ''
            raise ValidationError(_('Lỗi khi gửi yêu cầu tới VietinBank: code:  %s\n body: %s\n data_to_sign_check: %s\n payload: %s') % (error.code, body, data_to_sign, payload))
        except urllib.error.URLError as error:
            raise ValidationError(_('Lỗi kết nối tới VietinBank: %s') % error.reason)
        except http.client.RemoteDisconnected:
            raise ValidationError(_('Máy chủ VietinBank đã đóng kết nối đột ngột (RemoteDisconnected). Có thể do IP chưa được whitelist trên hệ thống VietinBank.'))
        except ConnectionResetError:
            raise ValidationError(_('Kết nối tới VietinBank bị reset (ConnectionResetError). Vui lòng kiểm tra mạng hoặc IP whitelist.'))
        except Exception as e:
            raise ValidationError(_('Lỗi không xác định khi kết nối tới VietinBank: %s') % str(e))

    def _send_bank_request_tk_name(self, payload, data_to_sign):
        self.ensure_one()
        if not self.bank_api_url_tk_name:
            _logger.warning(_('TK_name URL API VietinBank chưa được cấu hình.'))
            return 500, '', 'URL API chưa được cấu hình'

        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'x-ibm-client-id': '6181ed54f6545743a5c6eb94762ae309',
            'x-ibm-client-secret': '9bf59095a68635448a87263a7c303281',
            'Accept': 'application/json'
        }


        request = urllib.request.Request(
            self.bank_api_url_tk_name,
            data=payload.encode('utf-8'),
            headers=headers,
            method='POST',
        )
        try:
            response = urllib.request.urlopen(request, timeout=60)
            body = response.read().decode('utf-8')            
            data = json.loads(body)
            status_code = data.get("status", {}).get("code") 
            status_message = data.get("status", {}).get("message", "")
            if str(status_code).strip() != "1":
                _logger.warning(_('TK_name error when send request to VietinBank status: status_code:  %s\n body: %s\n data_to_sign_check: %s\n payload: %s') % (status_code, body, data_to_sign, payload))
                return status_code, '', 'VietinBank trả về lỗi: code=%s, message=%s' % (status_code, status_message)
            else: 
                _logger.warning(_('TK_name send request to VietinBank status: code:  %s\n body: %s\n data_to_sign_check: %s\n payload: %s') % (status_code, body, data_to_sign, payload))   
                active_val = str(data.get('active', '')).lower().strip()
                if active_val == "true":
                    return status_code, data.get('accountName', None), ''
                else:
                    return status_code, '', 'Tài khoản không hoạt động (active=%s). Response: %s' % (data.get('active', ''), body)
        except urllib.error.HTTPError as error:
            body = error.read().decode('utf-8') if hasattr(error, 'read') else ''
            _logger.warning(_('TK_name error when send request to VietinBank: code:  %s\n body: %s\n data_to_sign_check: %s\n payload: %s') % (error.code, body, data_to_sign, payload))
            return 500, '', 'HTTPError %s: %s' % (error.code, body)
        except urllib.error.URLError as error:
            _logger.warning(_('TK_name error when send request to VietinBank: %s') % error.reason)
            return 500, '', 'URLError: %s' % error.reason
        except http.client.RemoteDisconnected:
            _logger.warning(_('TK_name error when send request to VietinBank (RemoteDisconnected).'))
            return 500, '', 'RemoteDisconnected'
        except ConnectionResetError:
            _logger.warning(_('TK_name error when send request to VietinBank (ConnectionResetError).'))
            return 500, '', 'ConnectionResetError'
        except Exception as e:
            _logger.warning(_('TK_name error when send request to VietinBank: %s') % str(e))
            return 500, '', str(e)
    
    def action_bank_transfer(self):
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_('Yêu cầu UNC phải được phê duyệt trước khi gửi.'))

        payload, data_to_sign = self._build_bank_payload()
       
        status_code, response_content = self._send_bank_request(payload, data_to_sign)       


    def do_action(self):
        # Determine partner: use partner_bank_id.partner_id if available, otherwise use partner_id
        partner = self.partner_bank_id.partner_id if self.partner_bank_id else self.partner_id
        journal = self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('type', '=', 'bank')], limit=1)

        available_payment_method_lines = journal._get_available_payment_method_lines('outbound')
        if not available_payment_method_lines:
            raise ValidationError(_("No available payment method lines for the selected journal. Please configure a payment method for this journal."))
        payment_vals = {
            'payment_request_id': self.id,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'date': fields.Date.context_today(self),
            'ref': self.note,
            'partner_id': partner.id,
            'amount': self.total_amount,
            'currency_id': self.company_currency_id.id,
            'journal_id': journal.id,
            'payment_method_line_id': available_payment_method_lines[0].id,
        }
        return self._do_action_create_payment(payment_vals)

    def _do_action_create_payment(self, payment_vals):
        new_payment = self.env['account.payment'].create(payment_vals)
        new_payment.message_post(body="Tạo thanh toán từ %s" % self._get_html_link())
        self.message_post(body="Thanh toán %s từ đã được tạo" % self._get_html_link())
        # new_payment.action_post()
        self.write({
            'state': 'done'
        })
        return {
            'name': _("Tạo thanh toán"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'res_id': new_payment.id,
        }

    def action_view_payment(self):
        return {
            'name': "Thanh toán",
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'domain': [('payment_request_id', '=', self.id)],
            'context': {
                'create': False,
            }
        }
        
    def action_view_invoice(self):
        return {
            'name': "Bút toán",
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('payment_request_id', '=', self.id)],
            'context': {
                'create': False,
                'edit': False,
            }
        }

    def action_cancel(self):
        if not self.trp_approve_reason_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reason',
                'res_model': 'trp.approve.config.reason',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_type': 'cancel',
                    'default_res_id': self.id,
                    'default_res_model': self._name,
                    'default_approve_next_action': 'action_cancel'
                },
            }
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('done'):
            self.approve_next_action = 'action_cancel'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve_cancel'
            res_approve = self.sudo().with_context(approve_type='cancel').create_approve()
        if not res_approve or not self.trp_approve_config_line_id:
            self.write({
                'state': 'cancel'
            })

    def action_draft(self):
        if not self.env.context.get('reason_provided'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Lý do thiết lập về nháp',
                'res_model': 'trp.approve.config.reason',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_type': 'draft',
                    'default_res_id': self.id,
                    'default_res_model': self._name,
                    'default_approve_next_action': 'action_draft',
                    'reason_provided': True
                },
            }
        self.write({'state': 'draft', 'trp_approve_config_line_id': False})

    def action_undo(self):
        self.write({
            'state': 'draft'
        })
        
    is_allowed_to_complete = fields.Boolean(compute='_compute_is_allowed_to_complete')

    def _compute_is_allowed_to_complete(self):
        for rec in self:
            rec.is_allowed_to_complete = (self.env.user.login == 'tannt@ccv.vn')

    def action_force_done(self):
        from odoo.exceptions import UserError
        from odoo import _
        if self.env.user.login != 'tannt@ccv.vn':
            raise UserError(_("Bạn không có quyền thực hiện thao tác này."))
        for rec in self:
            rec.with_context(skip_approve_done=True).write({'state': 'done'})
            self.env['mail.activity'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id)]).with_context(skip_approve_done=True).unlink()
            odoobot = self.env.ref('base.partner_root', raise_if_not_found=False)
            author_id = odoobot.id if odoobot else self.env.user.partner_id.id
            rec.message_post(body=_("Phiếu đã được ép Hoàn thành (Force Done) bởi Admin."), author_id=author_id)

    def action_force_draft(self):
        from odoo.exceptions import UserError
        from odoo import _
        if self.env.user.login != 'tannt@ccv.vn':
            raise UserError(_("Bạn không có quyền thực hiện thao tác này."))
        for rec in self:
            rec.with_context(skip_approve_done=True).write({'state': 'draft', 'trp_approve_config_line_id': False})
            self.env['mail.activity'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id)]).with_context(skip_approve_done=True).unlink()
            odoobot = self.env.ref('base.partner_root', raise_if_not_found=False)
            author_id = odoobot.id if odoobot else self.env.user.partner_id.id
            rec.message_post(body=_("Phiếu đã được ép về Nháp (Force Draft) bởi Admin."), author_id=author_id)

    def action_invoice_history(self):
        return {
            'name': self.name,
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'res_id': self.move_id.id,
            'context': {
                'create': False,
                'edit': False,
            }
        }

    @api.model
    def create_default_approve_config(self):
        approve_id = self.env['trp.approve.config'].search([('model_id.model', '=', self._name)])
        if not approve_id:
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            user_ids = [2]
            self.env['trp.approve.config'].create({
                'model_id': model_id.id,
                'trp_approve_config_line_ids': [
                    (0, 0, {
                        'level': 1,
                        'manager_type': 'manager',
                        'user_ids': user_ids,
                        'type': 'new',
                    }),
                    (0, 0, {
                        'level': 1,
                        'manager_type': 'manager',
                        'user_ids': user_ids,
                        'type': 'cancel',
                    })]
            })

    def action_confirm(self):
        self = self.sudo()
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('draft'):
            self.approve_next_action = 'action_confirm'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()

        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'draft':
                self.write({'state': 'approve'})
            elif self.state == 'approve':
                trp_approve_config_id = self.env['trp.approve.config'].search([('model_id.model', '=', 'payment.request')])
                self.update({
                    'state': 'approved',
                    'account_id': trp_approve_config_id.account_id.id if (not self.journal_id and not self.journal_id.default_account_id) else self.journal_id.default_account_id.id,
                    'destination_account_id':  trp_approve_config_id.destination_account_id,
                    'journal_id': trp_approve_config_id.journal_id.id if not self.journal_id else self.journal_id,
                })
                return

    def action_refuse(self):
        self = self.sudo()
        if not self.is_user_current:
            return
        if self.state == 'cancel':
            return
        # Không write state ở đây nữa - để wizard action_confirm xử lý
        # sau khi user đã điền lý do và bấm Xác nhận
        return {
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'trp.approve.config.reason',
            'type': 'ir.actions.act_window',
            'context': {
                'default_res_id': self.id,
                'default_res_model': self._name,
                'default_trp_approve_config_line_id': self.trp_approve_config_line_id.id,
            }
        }
    
    def action_create_payment(self):
        trp_approve_config_id = self.env['trp.approve.config'].search([('model_id.model', '=', 'payment.request')])
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'context': {
            	'default_payment_request_id': self.id,
                'default_amount': self.total_amount,
            	'default_journal_id': trp_approve_config_id.journal_id.id if not self.journal_id.id else self.journal_id.id,
            },
            'target': 'current'
        }    
    
    has_expense = fields.Boolean(default=False,copy=False,compute="_compute_has_expense")
    
    def _compute_has_expense(self):
        for rec in self:
            rec.has_expense = True if self.env['hr.expense.sheet'].search_count([('payment_request_id', '=', rec.id)]) else False
        
    def action_create_expense(self):
        self = self.sudo()
        if self.state == 'approved':
            trp_approve_config_id = self.env['trp.approve.config'].search([('model_id.model', '=', 'payment.request')])
            product_id = trp_approve_config_id.product_id
            journal_id = trp_approve_config_id.journal_id if not self.journal_id else self.journal_id
            if not product_id:
                return
            employee = self.env['hr.employee'].search([('user_partner_id','=',self.partner_id.id)])
            if self.payment_note_ids:
                expense_line_ids = [(0,0,{
                    'date': line.invoice_date,
                    'product_id': product_id.id,
                    'tax_ids': [(4, tax.id) for tax in product_id.taxes_id],
                    'name': line.name or 'Chi phí',
                    'total_amount': line.amount_total,
                    'employee_id': employee.id,
                }) for line in self.payment_note_ids]
            else:
                expense_line_ids = [(0,0,{
                    'date': self.date,
                    'product_id': product_id.id,
                    'name': self.note or 'Chi phí',
                    'total_amount': self.total_amount,
                    'employee_id': employee.id,
                })]
            kwargs = {
                'name': self.note or 'Chi phí',
                'employee_id': employee.id,
                'payment_type': self.type if self.type == 'cash' else 'bank',
                'partner_bank_id': self.partner_bank_id.id,
                'journal_id': journal_id.id,
                'payment_request_id': self.id,
                'state': 'approve',
                'expense_line_ids': expense_line_ids,
            }
            if self.type == 'cash':
                cash_journal = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', self.company_id.id)], limit=1)
                if cash_journal:
                    kwargs['bank_journal_id'] = cash_journal.id
            expense = self.env['hr.expense.sheet'].create(kwargs)
            expense.action_sheet_move_create()
            body = "Chi phí được tạo từ %s" % self._get_html_link()
            expense.message_post(body=body)
            return {
                'name': "Chi phí",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hr.expense.sheet',
                'res_id': expense.id,
            }
    
    def action_view_expense(self):
        return {
            'name': "Chi phí",
            'view_mode': 'tree,form',
            'res_model': 'hr.expense.sheet',
            'type': 'ir.actions.act_window',
            'domain': [('payment_request_id', '=', self.id)],
            'context': {
                'create': False,
            }
        }

    def write(self, vals):
        res = super(PaymentRequest, self).write(vals)
        self = self.sudo()
        activity_data = []
        activity_type = self.env.ref('hr_expense.mail_act_expense_approval')
        for rec in self:
            config_id = self.env['trp.approve.config'].search([('model_id.model', '=', rec._name)], limit=1)
            if rec.state == 'approved' and config_id.response_cash_id and config_id.response_bank_id:
                response_id = config_id.response_cash_id if rec.type == 'cash' else config_id.response_bank_id
                res_model_id = self.env['ir.model'].search([('model', '=', rec._name)], limit=1)
                activity_data.append({
                    'activity_type_id': activity_type.id or False,
                    'date_deadline': fields.Date.today(),
                    'user_id': response_id.id,
                    'res_id': rec.id,
                    'res_model': rec._name,
                    'res_model_id': res_model_id.id,
                })
            if rec.state in ('cancel', 'done'):
                self.env['mail.activity'].search([('res_id', '=', rec.id), ('res_model', '=', rec._name)]).action_done()
        if activity_data:
            self.env['mail.activity'].create(activity_data)
        return res
