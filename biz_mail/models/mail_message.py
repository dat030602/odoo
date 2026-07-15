from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class MailMessage(models.Model):
    _inherit = 'mail.message'
    _description = 'Mail message'
    
    is_forward = fields.Boolean(default=False)
    notified_partner_ids = fields.Many2many(copy=False)
    
    
    @api.model_create_multi
    def create(self, values_list):
        cxt = self._context
        if cxt.get('is_forward'):
            for i, values in enumerate(values_list, 0):
                values_list[i]['is_forward'] = True
                    
        return super(MailMessage, self).create(values_list)

