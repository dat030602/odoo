from odoo import models, fields
class ResBank(models.Model):
    _inherit = 'res.bank'
    napas_code = fields.Char(string='Napas code')