# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import smtplib
from socket import gaierror, timeout
from ssl import SSLError
import html2text
import idna
from odoo.tools import ustr

class BizappsFptSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = "Bizapps Fpt Config"
    
    fpt_client_id = fields.Char(string='Client ID', default='AAAA', help='Đăng ký trong ứng dụng (https://developer.sms.fpt.net/document/huong-dan-dang-ky-ung-dung)')
    fpt_client_secret = fields.Char(string='Client Secret', default='AAAA', help='Đăng ký trong ứng dụng (https://developer.sms.fpt.net/document/huong-dan-dang-ky-ung-dung)')
    fpt_type_endpoint = fields.Selection([("live", "Live endpoint"), ("sandbox", "Sandbox endpoint"),], string='Type Endpoint', help='API Gồm có 2 endpoint:- Live: `http://app.sms.fpt.net`; - Sandbox: `http://sandbox.sms.fpt.net`')
    fpt_brand_name = fields.Char(string='Brand Name', required=False, default='Brand name', help='Brandname đã đăng ký với FPT.(https://partner.sms.fpt.net/)')
    fpt_active = fields.Boolean(string='Active', default = False)
    
    @api.model
    def get_values(self):
        res = super(BizappsFptSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        res.update(
            fpt_client_id = IrDefault.get('res.config.settings', 'fpt_client_id'),
            fpt_client_secret = IrDefault.get('res.config.settings', 'fpt_client_secret'),
            fpt_type_endpoint = IrDefault.get('res.config.settings', 'fpt_type_endpoint') or "live",
            fpt_brand_name = IrDefault.get('res.config.settings', 'fpt_brand_name'),
            fpt_active = IrDefault.get('res.config.settings', 'fpt_active'),
        )
        return res
    
    def set_values(self):
        super(BizappsFptSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', "fpt_client_id", self.fpt_client_id or None)
        IrDefault.set('res.config.settings', "fpt_client_secret", self.fpt_client_secret or None)
        IrDefault.set('res.config.settings', "fpt_type_endpoint", self.fpt_type_endpoint or None)
        IrDefault.set('res.config.settings', "fpt_brand_name", self.fpt_brand_name or None)
        IrDefault.set('res.config.settings', "fpt_active", self.fpt_active or None)
        self.env['bizapps.fpt.token'].sudo().deactive_all_token()# Bỏ hiệu lực các token cũ
        
    def sms_fpt_check_connect(self):
        try:
            response = self.env['bizapps.fpt.token'].sudo().get_access_token()
            if not response or response.get('error', False):
                raise UserError(response.get('error', False) or "Error: Error requests api. (Fpt Config,...)")
        except UserError as e:
            # let UserErrors (messages) bubble up
            raise e
        except (UnicodeError, idna.core.InvalidCodepoint) as e:
            raise UserError(_("Invalid server name !\n %s", ustr(e)))
        except (gaierror, timeout) as e:
            raise UserError(_("No response received. Check server address and port number.\n %s", ustr(e)))
        except smtplib.SMTPServerDisconnected as e:
            raise UserError(_("The server has closed the connection unexpectedly. Check configuration served on this port number.\n %s", ustr(e.strerror)))
        except smtplib.SMTPResponseException as e:
            raise UserError(_("Server replied with following exception:\n %s", ustr(e.smtp_error)))
        except smtplib.SMTPException as e:
            raise UserError(_("An SMTP exception occurred. Check port number and connection security type.\n %s", ustr(e.smtp_error)))
        except SSLError as e:
            raise UserError(_("An SSL exception occurred. Check connection security type.\n %s", ustr(e)))
        except Exception as e:
            raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s", ustr(e)))
        finally:
            pass
        title = _("Connection Test Succeeded!")
        message = _("Everything seems properly set up!")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }