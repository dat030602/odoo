from odoo import models, fields


class MisaConfig(models.Model):
    _name = 'misa.config'
    _description = 'MISA Configuration'

    # ========== Basic Fields ==========
    name = fields.Char(string='Name')
    vat = fields.Char(string='Tax Code')

    # ========== API Configuration ==========
    user_name = fields.Char(string='User Name')
    user_password = fields.Char(string='Password')
    api_url = fields.Char(string='API URL')

    state = fields.Selection([
        ('new', 'New'),
        ('lock', 'Locked'),
    ], string='State', default='new')

    def action_lock(self):
        self.ensure_one()
        self.state = 'lock'

    def action_unlock(self):
        self.ensure_one()
        self.state = 'new'
    