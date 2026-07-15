# -*- coding: utf-8 -*-
from odoo import  fields, models, _
from ast import literal_eval
import requests
import json
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class BizappsFptToken(models.Model):
    _name = "bizapps.fpt.token"
    _description = "Bizapps Fpt Token"
    
    scope = fields.Char(string='Scope', help='Quyền yêu cầu truy cập')
    access_token = fields.Char(string='Access token', help='Access token FPT trả về.')
    expires_in = fields.Integer(string='Expires in', help='Thời gian hết hạn.')
    token_type = fields.Char(string='Token type', help='Kiểu access token')
    validity_date = fields.Datetime(string='Validity date', help='Ngày access token hết hạn.')
    active = fields.Boolean(string='Active', default = True)
    session_id = fields.Char(string='session_id')
    url_endpoint =  fields.Char(string='Url endpoint')
    brand_name = fields.Char(string='Brand Name', help='Brandname đã đăng ký với FPT.')
    
    def deactive_all_token(self):
        tokens = self.search([('active', '=', True)])
        for token in tokens:
            token.write({
                'active': False,
            })
        return True
    
    def get_token(self):
        IrDefault = self.env['ir.default'].sudo()
        grant_type = 'client_credentials'
        session_id = 5
        scope = 'send_brandname_otp'
        
        client_id = IrDefault.get('res.config.settings', 'fpt_client_id') or False
        client_secret = IrDefault.get('res.config.settings', 'fpt_client_secret') or False
        type_endpoint = IrDefault.get('res.config.settings', 'fpt_type_endpoint') or 'live'
        brand_name = IrDefault.get('res.config.settings', 'fpt_brand_name') or False
        active = IrDefault.get('res.config.settings', 'fpt_active') or False
        
        if active:
            url_endpoint = 'api01.sms.fpt.net'
            if type_endpoint == 'sandbox':
                url_endpoint = 'sandbox.sms.fpt.net'
                
            if grant_type and client_id and client_secret and scope and session_id and url_endpoint and brand_name:
                url_api = "http://%s/oauth2/token"%(url_endpoint)
                headers = {
                    "content-type":"application/json",
                }
                data = {
                    "grant_type": grant_type,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                    "session_id": session_id,
                }
            else:
                return {
                    'error' :_('Please Configuration the required values!'),
                }
            r = requests.post(
                url=url_api,
                headers=headers,
                data=json.dumps(data)
            )
            pastebin_url = r.text
            print("pastebin_url",pastebin_url)
            url_json = json.loads(pastebin_url)
            error_description = url_json.get('error_description')
            error = url_json.get('error')
            access_token = url_json.get('access_token')
            expires_in = url_json.get('expires_in')
            token_type = url_json.get('token_type')
            scope = url_json.get('scope')
            if error_description:
                value_log = {
                    'url': url_api,
                    'create_on': datetime.now(),
                    'data': str(json.dumps(data)),
                    'state': 'fail',
                    'error': 'Error(%s): %s' % (error, error_description),
                }
                print('#################', value_log)
                self.env['sms.fpt.log'].create(value_log)
                return {
                    'error' :_('get_token failed error(%s): %s'%(error, error_description)),
                }
            else:
                if access_token:
                    env_token = self.sudo()
                    expires = expires_in / 3600 
                    validity_date = datetime.now()  + timedelta(hours=(expires))
                    data = {
                        'access_token' : access_token,
                        'expires_in' : expires_in,
                        'token_type' : token_type,
                        'scope' : scope,
                        'validity_date' : validity_date,
                        'active': True,
                        'session_id': session_id,
                        'url_endpoint': url_endpoint,
                        'brand_name': brand_name,
                    }
                    token_id = env_token.search([('access_token', '=', access_token)])
                    env_token.deactive_all_token()# Bỏ hiệu lực các token cũ
                    result_token = {}
                    if token_id:
                        token_id.write(data)
                    else:
                        token_id = env_token.create(data)
                    return {
                        "token_id": token_id,
                        'error': False
                    }
        return {
            'error' :_('Client không được cấp phép. Vui lòng cấu hình và cho phép gửi tin nhắn!')
        }
    
    def get_access_token(self):
        today = datetime.today()
        today_time = datetime.strftime(today, DEFAULT_SERVER_DATETIME_FORMAT)
        token_id = self.search([('active', '=',True),('validity_date', '>', today_time)], limit=1)        
        IrDefault = self.env['ir.default'].sudo()
        brand_name = IrDefault.get('res.config.settings', 'fpt_brand_name') or False
        active = IrDefault.get('res.config.settings', 'fpt_active') or False
        type_endpoint = IrDefault.get('res.config.settings', 'fpt_type_endpoint') or 'live'
        url_endpoint = 'api01.sms.fpt.net'
        if type_endpoint == 'sandbox':
            url_endpoint = 'sandbox.sms.fpt.net'
        error = _('Client không được cấp phép. Vui lòng cấu hình và cho phép gửi tin nhắn!')
        if active:
            if token_id:
                if token_id.brand_name != brand_name:
                    token_id.write({'brand_name': brand_name})
            else:
                result_token = self.sudo().get_token() # get token khi chưa có hoặc hết hạn
                if not result_token.get('error', False):
                    token_id = result_token.get('token_id', False)
                else:
                    error = result_token.get('error')
            if token_id:
                return {
                    'brand_name': brand_name,
                    'url_endpoint': url_endpoint,
                    'scope': token_id.scope,
                    'access_token': token_id.access_token,
                    'expires_in': token_id.expires_in,
                    'token_type': token_id.token_type,
                    'active': token_id.active,
                    'session_id': token_id.session_id,
                    'error' : False,
                }
        return {
            'error': error
        }
