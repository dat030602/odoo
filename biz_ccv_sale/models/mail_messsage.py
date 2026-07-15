from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class MailMessage(models.Model):
    _inherit = 'mail.message'
    _description = 'Mail message'
    
    skip = fields.Boolean(default=False)
    
    
    @api.model_create_multi
    def create(self, values_list):
        if any(values.get('skip') for values in values_list):
            return self
                    
        return super(MailMessage, self).create(values_list)

