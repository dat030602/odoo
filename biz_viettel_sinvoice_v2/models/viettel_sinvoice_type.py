# -*- coding: utf-8 -*-
from odoo import fields, models, _,api
import re
import json, urllib.parse
from odoo.exceptions import UserError
import requests
import sys
import logging
import smtplib
from socket import gaierror, timeout
from ssl import SSLError
import html2text
import idna
from odoo.tools import ustr

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')
SMTP_TIMEOUT = 60
PY3 = sys.version_info >= (3,0)
from datetime import date

if PY3:
    unichr = chr
    xrange = range
    unicode = str
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass
    
class ViettelSInvoiceType(models.Model):
    _name = 'viettel.sinvoice.type'
    _description = 'Viettel S-Invoice Type'
    
    name = fields.Char(string='Name')
    odoo_code = fields.Char('Odoo Code')
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
    template = fields.Char(string='Template')
    series = fields.Char(string='Series')
    customer_field_ids = fields.One2many('viettel.sinvoice.customer.fields','sinvoice_type_id',string="Customer Fields")

    def vsi_get_customer_fields(self, config_id, vsi_template):
        api_url = config_id.vsi_domain + '/services/einvoiceapplication/api/InvoiceAPI/InvoiceWS/getCustomFields?taxCode=%s&templateCode=%s'%(
            config_id.vsi_tin,vsi_template
        )
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % config_id.vsi_access_token,

        }
        succeed = False
        print("~~~!!api_url",api_url)
        print("~~~!!headers",headers)
        result = requests.get(api_url, headers=headers)
        output = json.loads(result.text)
        if result.status_code == 200:
            print("~~~output",output)
            if output.get('customFields',False):
                self.customer_field_ids.unlink()
                env_custom_field = self.env['viettel.sinvoice.customer.fields'].sudo()
                for custom_field in output.get('customFields'):
                    custom_data = {
                        'sinvoice_type_id': self.id,
                        'field_id': custom_field.get('id', False),
                        'keyLabel': custom_field.get('keyLabel', False),
                        'valueType': custom_field.get('valueType', False),
                        'invoiceTemplatePrototypeId': custom_field.get('invoiceTemplatePrototypeId', False),
                        'keyTag': custom_field.get('keyTag', False),
                        'isSeller': custom_field.get('isSeller', False),
                        'isRequired': custom_field.get('isRequired', False),
                    }
                    exist_id = env_custom_field.search([
                        ('field_id','=',custom_field.get('id', False)),
                        ('sinvoice_type_id','=',self.id),
                        ], limit=1)
                    if not exist_id:
                        env_custom_field.create(custom_data)

            else:
                raise UserError("Warning: vsi_get_customer_fields: %s"% vsi_template)

        else:
            if result.status_code == 401 and output.get('error', '') == 'invalid_token':
                if config_id.sinvoice_refresh_token():
                    return self.vsi_get_customer_fields(config_id, vsi_template)
            raise UserError("Connection errors: %s" % (result.text))
        return True

class SInvoiceCustomFields(models.Model):
    _name = 'viettel.sinvoice.customer.fields'
    _description = 'Viettel SInvoice Custom Fields'

    sinvoice_type_id = fields.Many2one('viettel.sinvoice.type', string="Sinvoice Type")
    field_id = fields.Char(string="Field ID")
    keyLabel = fields.Char(string="Key Label")
    valueType = fields.Char(string="Value Type")
    invoiceTemplatePrototypeId = fields.Char(string="Invoice Template Prototype Id")
    keyTag = fields.Char(string="Key Tag")
    isSeller = fields.Char(string="is Seller")
    isRequired = fields.Char(string="is Required")