# -*- coding: utf-8 -*-

import requests
import json
import base64
import logging

from odoo import fields, models
from datetime import datetime

_logger = logging.getLogger(__name__)


class BizappsFptSms(models.Model):
    _name = "bizapps.fpt.sms"
    _rec_name = 'phone'
    _order = 'create_date desc'
    _description = "Bizapps Fpt Sms"
    
    message_id = fields.Char(string='Message Id',help = "Id của tin brandname gửi đi.")
    phone = fields.Char(string='Phone', required="1", help="Số điện thoại nhận tin nhắn. Định dạng 84xxx, 0xxx. Ví dụ: 84949123456 hoặc 0949123456.")
    message = fields.Char(string='Message', required="1", help="Nội dung tin nhắn gửi đi, không dùng các ký tự đặc biệt như: # & [] {}.")
    partner_id = fields.Char(string='PartnerId', help='ID của đối tác FPT')
    telco = fields.Char(string='Telco', help='Nhà mạng của thuê bao khách hàng.')
    date_sent = fields.Datetime(string='Date sent')
    active = fields.Boolean(string='Active', default = True)
    state = fields.Selection([('draft','Draft'),('sent','Done'),('cancel','Cancel'),('error','Error')],'Status', default='draft')
    IsSent = fields.Boolean(string='IsSent', default = False)
    error_detail = fields.Char(string="Error detail")

    phone_odoo = fields.Char(string="Phone Odoo", copy=False)
    is_happy_birthday_sms_fpt = fields.Boolean(string="Happy Birthday SMS", copy=False)
    is_order_confirmation_sms_fpt = fields.Boolean(string="SMS Order Confirmation", copy=False)
    is_order_completion_sms_fpt = fields.Boolean(string="SMS Order Completion", copy=False)

    def action_sent(self):
        if self.phone and self.message:
            self.sent_sms_api(self.phone, self.message)
        return True
    
    def sent_sms_api(self,phone=False, message = False):
        sms = self
        if phone and message:
            env_token = self.env['bizapps.fpt.token'].sudo()
            token = env_token.get_access_token()
            if type(token) == dict and token.get('error'):
                value = {
                    'phone': phone,
                    'message': message,
                    'state': 'error',
                    'date_sent' : datetime.now(),
                    'error_detail': token.get('error'),
                }
                if self:
                    self.write(value)
                else:
                    sms = self.create(value)
                return sms
            if token:
                url_api = 'http://%s/api/push-brandname-otp'%(token.get('url_endpoint'))
                message_encode = message.encode()
                message_base64 = base64.b64encode(message_encode)
                data ={
                    "access_token": token.get('access_token'),
                    "session_id": token.get('session_id'),
                    "Phone": phone,
                    "Message": message_base64.decode("utf-8") ,
                    "BrandName": token.get('brand_name'),
                }
                headers = {
                    "content-type":"application/json",
                }
                r = requests.post(
                    url=url_api,
                    headers=headers,
                    data=json.dumps(data)
                )
                pastebin_url = r.text
                url_json = json.loads(pastebin_url)
                error = url_json.get('error')
                error_description = url_json.get('error_description')
                MessageId = url_json.get('MessageId')
                Phone = url_json.get('Phone')
                BrandName = url_json.get('BrandName')
                Message = url_json.get('Message')
                PartnerId = url_json.get('PartnerId')
                Telco = url_json.get('Telco')
                IsSent = url_json.get('IsSent')
                if error_description:
                    value = {
                        'phone': phone,
                        'message': message,
                        'state': 'error',
                        'date_sent' : datetime.now(),
                        'error_detail': 'Error(%s): %s'%(error, error_description),
                    }
                    value_log = {
                        'url': url_api,
                        'create_on': datetime.now(),
                        'data': str(json.dumps(data)),
                        'state': 'fail',
                        'error': 'Error(%s): %s' % (error, error_description),
                    }
                    print('#################', value_log)
                    self.env['sms.fpt.log'].create(value_log)
                    if self:
                        self.write(value)
                    else:
                        self.create(value)
                    return False
                    #raise UserError(_('Error(%s): %s'%(error, error_description)))
                else:
                    value = {
                        'message_id' : MessageId,
                        'phone': Phone,
                        'message': Message,
                        'partner_id' : PartnerId,
                        'telco': Telco,
                        'IsSent': IsSent,
                        'active':True,
                        'state': 'sent',
                        'date_sent' : datetime.now(),
                        'phone_odoo': phone
                    }
                    value_log = {
                        'url': url_api,
                        'create_on': datetime.now(),
                        'data': str(json.dumps(data)),
                        'state': 'success',
                        'error': '',
                        'data_response': token.get('access_token'),
                    }
                    self.env['sms.fpt.log'].create(value_log)
                    if self:
                        self.write(value)
                    else:
                        sms = self.create(value)
        return sms

    def action_resent(self):
        self.action_sent()
        return False
    
    def state_error(self):
        value = {
            'state': 'error',
        }
        self.write(value)
        return True
    
    def action_cancel(self):
        value = {
            'state': 'cancel',
            'active': False,
        }
        self.write(value)
        return True

    def action_check_had_sent_sms_birthday(self, phone=False):
        today = datetime.today()
        sms_fpt = self.search([
            ("is_happy_birthday_sms_fpt", "=", True),
            ("phone_odoo", "=", phone)
        ]).filtered(lambda x: x.create_date.year == today.year)
        if sms_fpt:
            return True
        else:
            return False

    def _cron_send_happy_birthday_sms(self):
        _logger.info("=== RUN CRON SEND HAPPY BIRTHDAY SMS ===")
        try:
            today = datetime.today()

            fpt_template = self.env['sms.template']
            happy_birthday_template = fpt_template.search([("model_id", "!=", False), ("fpt_template_type", '=', "happy_birthday")])
            if not happy_birthday_template:
                return

            for template in happy_birthday_template:
                if template.time_from_fpt and template.time_to_fpt:
                    if template.time_from_fpt.date() <= today.date() <= template.time_to_fpt.date():
                        fpt_template += template
                else:
                    fpt_template += template

            for template in fpt_template:
                records = False
                fpt_sms_phone = self.search([("phone", "!=", False), ("is_happy_birthday_sms_fpt", "=", True)]).filtered(lambda x: x.create_date.year == today.year).mapped("phone_odoo")
                ir_model = self.env[template.model_id.model]
                if template.model_id.model == "res.partner":
                    records = ir_model.search([
                        ("fpt_date_of_birth", "!=", False)
                    ]).filtered(lambda x: x.fpt_date_of_birth.day == today.day and x.fpt_date_of_birth.month == today.month)
                    records = records.filtered(lambda x: x.phone not in fpt_sms_phone)
                elif template.model_id.model == "hr.employee":
                    records = ir_model.search([("birthday", "!=", False)]).filtered(lambda x: x.birthday.day == today.day and x.birthday.month == today.month)
                    records = records.filtered(lambda x: x.mobile_phone not in fpt_sms_phone)
                if not records:
                    return

                for record in records:
                    if template.model_id.model == "res.partner":
                        phone = record.phone
                    elif template.model_id.model == "hr.employee":
                        phone = record.mobile_phone
                    body = template._render_field('body', record.ids, set_lang=record.lang or 'vi_VN')[record.id]
                    sms = self.sent_sms_api(phone, body)
                    if sms:
                        sms.update({"is_happy_birthday_sms_fpt": True})
        except Exception as error:
            _logger.warning(error)



