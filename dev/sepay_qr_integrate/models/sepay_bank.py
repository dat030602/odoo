from odoo import models, fields, api, _
import requests
import base64
from odoo.tools import image_process

def get_image_from_url(url):
    if url:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                return image_base64
        except Exception:
            pass
    return False

class SepayBank(models.Model):
    _name = 'sepay.bank'
    _description = 'Sepay Bank Information'

    name = fields.Char('Bank Name')
    code = fields.Char('Bank Code')
    bin = fields.Char('Bank BIN')
    short_name = fields.Char('Short Name')
    supported = fields.Boolean('Supported')
    logo_url = fields.Char(string="Logo URL")
    logo_image = fields.Binary(string="Logo", max_width=200, max_height=200, attachment=False, stored=True, compute="_compute_logo")
    
    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            name_display = f"{record.code} - {record.name}" if record.code else record.name
            record.display_name = name_display

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            domain += [
                '|', '|',
                ('code', operator, name),
                ('name', operator, name),
                ('short_name', operator, name),
            ]
        return self._search(domain, limit=limit, order=order)
    
    @api.depends('logo_url')
    def _compute_logo(self):
        for rec in self:
            logo_image = get_image_from_url(rec.logo_url)
            rec.logo_image = image_process(logo_image.encode('utf-8')) if logo_image else None

    @api.model
    def fetch_banks(self, *args, **kwargs):
        """Fetch banks from Sepay API"""
        url = "https://qr.sepay.vn/banks.json"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json().get('data', [])
                for bank_data in data:
                    # Check if bank already exists
                    existing_bank = self.search([('code', '=', bank_data.get('code'))], limit=1)
                    vals = {
                        'name': bank_data.get('name', ''),
                        'bin': bank_data.get('bin', ''),
                        'short_name': bank_data.get('short_name', ''),
                        'supported': bank_data.get('supported', False),
                    }
                    if existing_bank:
                        existing_bank.write(vals)
                    else:
                        vals.update({'code': bank_data.get('code', '')})
                        self.create(vals)
                # Notify success after processing all banks
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
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Failed to fetch banks from Sepay API.'),
                        'type': 'danger',
                        'sticky': False,
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error fetching banks: %s') % str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

