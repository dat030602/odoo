# -*- coding: utf-8 -*-

import json
import urllib.error
import urllib.request
import base64
import logging
import unicodedata
import os
import http.client
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource
from datetime import datetime, timezone, timedelta



try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    hashes = serialization = padding = None

_logger = logging.getLogger(__name__)


class PaymentRequestUNC(models.Model):
    _name = 'payment.request.unc'
    _inherit = 'payment.request'
    _description = 'Ủy nhiệm chi'

    bank_api_url = 'https://api.vietinbank.vn/vtb/public/erp/v1/payment/transfer'
    bank_providerId = fields.Char(string='VietinBank providerId', help='Partner code for VietinBank API authentication.')
    bank_transaction_id = fields.Char(string='Bank Transaction ID', copy=False)
    bank_response_code = fields.Char(string='Bank Response Code', copy=False)
    bank_response_message = fields.Char(string='Bank Response Message', copy=False)
    bank_request_payload = fields.Text(string='Bank Request Payload', copy=False)
    bank_response_payload = fields.Text(string='Bank Response Payload', copy=False)

    beneficiary_account = fields.Char(string='Số tài khoản thụ hưởng')
    beneficiary_name = fields.Char(string='Tên người thụ hưởng')
    beneficiary_bank_id = fields.Many2one('res.bank', string='Ngân hàng thụ hưởng')
    beneficiary_bank_code = fields.Char(string='Mã Napas ngân hàng thụ hưởng')

    partner_id = fields.Many2one("res.partner", string="Đối tượng thanh toán", related="user_id.partner_id", store=True)
    total_amount = fields.Monetary(string="Số tiền", readonly=False, currency_field='currency_id')
    journal_id = fields.Many2one('account.journal', string="Sổ nhật ký")
    type = fields.Selection([('transfer', 'Chuyển khoản'), ('cash', 'Tiền mặt')], string="Hình thức thanh toán", default="transfer", readonly=True)
    hide_bank_config = fields.Boolean(string='Ẩn Cấu hình ngân hàng', default=True)
    partner_bank_id = fields.Many2one('res.partner.bank', string="Tài khoản gửi")
    partner_name = fields.Char(string="Tên người gửi")
    vietinbank_bank_id ="01201001"


    @api.onchange('beneficiary_bank_id')
    def _onchange_beneficiary_bank_id(self):
        if self.beneficiary_bank_id:
            self.beneficiary_bank_code = getattr(self.beneficiary_bank_id, 'napas_code', False) or ''

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('payment.request.unc') or 'New'
        return super(PaymentRequestUNC, self).create(vals)

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
        
        beneficiary_account_input = self.beneficiary_account
        if len(beneficiary_account_input) < 6:
            raise ValidationError(_('Số tài khoản thụ hưởng không hơp lệ'))

        sender_account_input = self.partner_bank_id.acc_number
        if len(sender_account_input) < 6:
            raise ValidationError(_('Số tài khoản gửi không hơp lệ'))

        sender_name_input = self._remove_vietnamese_accents(self.partner_name or self.partner_bank_id.acc_holder_name)
        beneficiary_name_input = self._remove_vietnamese_accents(self.beneficiary_name)
   
        beneficiary_bank_code_input = self.beneficiary_bank_code
        if len(beneficiary_bank_code_input) < 4:
            raise ValidationError(_('Mã ngân hàng thụ hưởng không hợp lệ')) 
 
        message_transfer = self._remove_vietnamese_accents(self.note)
        public_ip = None        
        with urllib.request.urlopen("https://api.ipify.org") as response:
            public_ip = response.read().decode("utf-8")

        transType = "np"
        if (beneficiary_bank_code_input == self.vietinbank_bank_id):
            transType = "in"
        
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
                    "recvAcctName": self._remove_vietnamese_accents(self.beneficiary_name),              
                    "recvAddr": "", 
                    "remark": message_transfer,  
                    "currencyCode": "VND",         
                    "senderBankId": self.vietinbank_bank_id, #ngan hàng cung cap
                    "senderBranchId": self.vietinbank_bank_id, #ngan hàng cung cap --để trống hoặc lây giông bankId được
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
    
    def _remove_vietnamese_accents(self, text):
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
            if status_code != "1":
                raise ValidationError(_('Lỗi khi gửi yêu cầu tới VietinBank status: code:  %s\n body: %s\n data_to_sign_check: %s\n payload: %s') % (status_code, body, data_to_sign, payload))
            else:
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

    def do_action(self):
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_('Yêu cầu UNC phải được phê duyệt trước khi gửi.'))

        payload, data_to_sign = self._build_bank_payload()
        self.bank_request_payload = payload
        status_code, response_content = self._send_bank_request(payload, data_to_sign)
        self.bank_response_payload = response_content
        self.bank_response_code = str(status_code)

        try:
            response_data = json.loads(response_content)
            self.bank_transaction_id = response_data.get('transactionId') or response_data.get('transaction_id') or response_data.get('reference')
            self.bank_response_message = response_data.get('message') or response_data.get('description') or ''
        except Exception:
            self.bank_response_message = _('Không thể phân tích phản hồi từ ngân hàng.')

        return super(PaymentRequestUNC, self).do_action()
