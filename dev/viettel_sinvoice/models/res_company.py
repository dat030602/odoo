from odoo import models, fields
import requests
import json
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    vsi_domain = fields.Char('Domain', default="https://api-vinvoice.viettel.vn/services/einvoiceapplication/api")
    vsi_tin = fields.Char('TIN', default='0301714093')
    vsi_username = fields.Char('Username', default='0301714093')
    vsi_password = fields.Char('Password', default='12345678a@A')
    vsi_template = fields.Char('Template', default='01GTKT0/003')
    vsi_series = fields.Char('Series', default='VM/21E')
    vsi_type = fields.Many2one('viettel.sinvoice.type', 'Invoice Type')

    def get_access_token(self):
        base_url = 'https://api-vinvoice.viettel.vn/auth/login'
        header = {
            'Content-Type': 'application/json'
        }
        body = {
            'username': self.vsi_username,
            'password': self.vsi_password
        }
        try:
            resp = requests.post(base_url, headers=header, json=body, timeout=15)
            result = json.loads(resp.text)
            access_token = result.get('access_token')
            if access_token:
                return access_token
            else:
                return ''
        except Exception as e:
            raise UserError('Lỗi kết nối dịch vụ: %s' % e)

    def check_vsi_server(self):
        headers = {"Content-type": "application/json; charset=utf-8"}
        company_id = self
        api_url = company_id.vsi_domain + '/InvoiceAPI/InvoiceUtilsWS/getProvidesStatusUsingInvoice'
        data = {
            "supplierTaxCode": company_id.vsi_tin,
            "templateCode": company_id.vsi_template,
            "serial": company_id.vsi_series,
        }
        access_token = self.get_access_token()
        headers = {
            "Content-type": "application/json; charset=utf-8",
            'Cookie': 'access_token=%s' % access_token
        }

        result = requests.post(api_url, json=data, headers=headers, timeout=15)

        if result.status_code == 200:
            output = json.loads(result.text)
            if not output['errorCode'] and not output['description']:
                raise UserError("Số hóa đơn đã sử dụng %s / %s" % (output['numOfpublishInv'], output['totalInv']))
            else:
                raise UserError("%s\n%s" % (output['errorCode'], output['description']))
        else:
            raise UserError("Lỗi kết nối: %s" % (result.status_code))
