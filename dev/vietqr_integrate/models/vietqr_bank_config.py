from odoo import models, fields, api, _
import requests
import base64
from odoo.tools import image_process

def get_image_from_url(url):
    if url:
        response = requests.get(url)
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            return image_base64
    return False

class VietQRBankConfig(models.Model):
    _name = 'vietqr.bank.config'
    _description = 'VietQR Bank Config'

    name = fields.Char('Bank Name')
    code = fields.Char('Bank Code')
    swift_code = fields.Char('Swift Code')
    bin = fields.Char('Bank BIN')
    transfer_supported = fields.Boolean('Supports Transfer')
    lookup_supported = fields.Boolean('Supports Lookup')
    is_transfer = fields.Boolean('Is Transfer Enabled')
    logo_url = fields.Char(string="Logo")
    logo_image = fields.Binary(string="Logo", max_width=200, max_height=200, attachment=False, stored=True, compute="_compute_logo")
    
    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            name_display = f"{record.code} - {record.name}" if record.code else record.name
            record.display_name = name_display
    
    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        args = list(domain or [])
        if name :
            args += [
                '|',
                ('code', operator, name),
                ('name', operator, name)
            ]
        return self._search(args, limit=limit, order=order)
    
    @api.depends('logo_url')
    def _compute_logo(self):
        for rec in self:
            logo_image = get_image_from_url(rec.logo_url)
            rec.logo_image = image_process(logo_image.encode('utf-8')) if logo_image else None

    @api.model
    def fetch_banks(self, *args, **kwargs):
        url = "https://api.vietqr.io/v2/banks"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('data', [])
            try:
                for bank in data:
                    existing_bank = self.search([('code','=',bank.get('code',False))], limit=1)
                    vals = {
                        'name': bank.get('name',False),
                        'swift_code': bank.get('swift_code',False),
                        'logo_url': bank.get('logo',False),
                        'bin': bank.get('bin',False),
                        'transfer_supported': bank.get('transferSupported',0) == 1,
                        'lookup_supported': bank.get('lookupSupported',0) == 1,
                        'is_transfer': bank.get('isTransfer',0) == 1,
                    }
                    if existing_bank:
                        existing_bank.write(vals)
                    else:
                        vals.update({'code': bank.get('code',False)})
                        self.create(vals)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Banks have been fetched successfully.'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('An error occurred while processing bank data: %s' % str(e)),
                        'type': 'danger',
                        'sticky': False,
                    }
                }

