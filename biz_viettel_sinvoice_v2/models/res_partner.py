from odoo import models, fields, api, _
import re

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    address_invoice_vat = fields.Char('Address Vat')
    name_vat = fields.Char('Name Vat')
    id_type = fields.Selection([
        ('1','ID card'),
        ('2','Business license'),
        ('3','Passport'),
    ],'Id Type')
    identity_card = fields.Char('Identity Card')
    
    @api.model
    def _commercial_fields(self):
        return ['credit_limit']

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        return

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        return

    @api.onchange('phone')
    def validate_phone(self):
        if self.phone:
            if not re.match(r'^([\s\d]+)$', self.phone):
                self.phone = self._origin and self._origin.phone or False
                return {'warning': {
                    'title': _('Warning'),
                    'message': _('Phone numbers invalid')
                }}
