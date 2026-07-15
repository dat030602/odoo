# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource

import json
import urllib.error
import urllib.request
import base64
import logging
import unicodedata
import os
import http.client
from datetime import datetime, timezone, timedelta

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    hashes = serialization = padding = None

_logger = logging.getLogger(__name__)

class AlphaInternalAccount(models.Model):
    _inherit = 'alpha.internal.account'

    partner_name = fields.Char(string="Người thụ hưởng", compute="_compute_partner_name", store=True, readonly=False)
    payment_note_ids = fields.One2many('payment.product.note','alpha_internal_account_id')
    
    amount_untax_total = fields.Monetary("Tổng chưa thuế", compute="_compute_total_amounts", store=True)
    amount_tax_total = fields.Monetary("Tổng thuế", compute="_compute_total_amounts", store=True)
    amount_total = fields.Monetary("Tổng cộng", compute="_compute_total_amounts", store=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id.id)
    currency_name = fields.Char(related='currency_id.name', string='Currency Name')
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    note = fields.Char("Nội dung")
    note_chuyen_khoan = fields.Char("Nội dung Chuyển khoản")

    @api.depends('payment_note_ids.amount_untax', 'payment_note_ids.amount_tax', 'payment_note_ids.amount_total')
    def _compute_total_amounts(self):
        for rec in self.sudo():
            rec.amount_untax_total = sum(rec.payment_note_ids.mapped('amount_untax'))
            rec.amount_tax_total = sum(rec.payment_note_ids.mapped('amount_tax'))
            rec.amount_total = sum(rec.payment_note_ids.mapped('amount_total'))
            if rec.amount_total != 0:
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

    bank_api_url = 'https://api.vietinbank.vn/vtb/public/erp/v1/payment/transfer'
    bank_api_url_tk_name = 'https://api.vietinbank.vn/vtb/public/erp/v1/account/benAcctInq'

    fixed_sender_tk = fields.Many2one('res.partner.bank', string="Tài khoản gửi", default=lambda self: self.env['res.partner.bank'].search([('acc_number', '=', '110002630105')], limit=1))
    fixed_sender_tk_name = fields.Char(string="Tên người gửi", default='CTY TNHH CON CO VANG')
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
                    error_msg = getattr(e, 'name', str(e))
                    return {
                        'warning': {
                            'title': 'Lỗi kết nối VietinBank', 
                            'message': error_msg
                        }
                    }

    @api.depends('partner_bank_id')
    def _compute_partner_napas_code(self):
        for rec in self:
            if rec.partner_bank_id and rec.partner_bank_id.bank_id and hasattr(rec.partner_bank_id.bank_id, 'napas_code'):
                rec.partner_napas_code = rec.partner_bank_id.bank_id.napas_code
            else:
                rec.partner_napas_code = False

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

        if self.currency_id.name.lower() != 'vnd':
            raise ValidationError(_('Chỉ hỗ trợ thanh toán bằng VND.'))
            
        if self.state != 'approved':
            raise ValidationError(_('Yêu cầu phải được phê duyệt trước khi gửi.'))

        payload, data_to_sign = self._build_bank_payload()
        status_code, response_content = self._send_bank_request(payload, data_to_sign)       

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

    def write(self, vals):
        res = super(AlphaInternalAccount, self).write(vals)
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
