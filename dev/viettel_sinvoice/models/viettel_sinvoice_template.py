# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_HEADER = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8'
}

class ViettelSInvoiceTemplate(models.Model):
    _name = 'viettel.sinvoice.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Viettel S-Invoice Template'

    active = fields.Boolean(default=True)
    branch_id = fields.Many2one('company.branch', 'Branch', tracking=True, ondelete='restrict', required=True)
    vat = fields.Char(related='branch_id.vat', store=True)
    type_id = fields.Many2one('viettel.sinvoice.type', 'Invoice Type', tracking=True, required=True)
    invoice_type_code = fields.Char(related='type_id.code', store=True, string='Invoice Type Code')
    template_code = fields.Char('Template Code', tracking=True, required=True)  # Mẫu hoá đơn
    series = fields.Char('Series', tracking=True, copy=False, required=True)  # Ký hiệu hoá đơn
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('branch_template_series_uniq', 'unique (branch_id, template_code, series)',
         'The combination of Branch, Template and Series must be unique!'),
    ]
    @api.depends('vat', 'invoice_type_code', 'template_code', 'series')
    def _compute_display_name(self):
        for record in self:
            name_display = "%s / %s / %s / %s" % (record.vat, record.invoice_type_code, record.template_code, record.series)
            record.display_name = name_display

    def get_info_dynamic_fields(self):
        data = {
            'taxCode': self.vat,
            'templateCode': self.template_code
        }
        endpoint = self.env.company.vsi_domain + '/InvoiceAPI/InvoiceWS/getCustomFields'
        access_token = self.company_id.get_access_token()
        headers = {
            "Content-type": "application/json; charset=utf-8",
            'Cookie': 'access_token=%s' % access_token
        }
        resp = requests.get(endpoint, params=data, headers=headers)
        try:
            values = resp.text
            raise UserError(values)
        except Exception as e:
            _logger.info('======== Fail while executing authentication request =========: State code %s, Detail %s' %
                         (resp.status_code, e))
            raise

    def check_vsi_server(self):
        api_url = self.company_id.vsi_domain + '/InvoiceAPI/InvoiceUtilsWS/getProvidesStatusUsingInvoice'
        data = {
            "supplierTaxCode": self.vat,
            "templateCode": self.template_code,
            "serial": self.series,
        }
        access_token = self.company_id.get_access_token()
        headers = {
            "Content-type": "application/json; charset=utf-8",
            'Cookie': 'access_token=%s' % access_token
        }
        result = requests.post(api_url, json=data, headers=headers)
        if result.status_code == 200:
            output = json.loads(result.text)
            if not output['errorCode'] and not output['description']:
                raise UserError("Số hóa đơn đã sử dụng %s / %s" % (output.get('numOfpublishInv', 'N/A'), output.get('totalInv', 'N/A')))
            else:
                raise UserError("%s\n%s" % (output.get('errorCode', 'N/A'), output.get('description', 'N/A')))
        else:
            raise UserError("Lỗi kết nối: %s" % result.status_code)
