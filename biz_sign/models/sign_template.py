from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
        
class SignTemplate(models.Model):
    _inherit = 'sign.template'
    _description = "Signature Template"

    def action_sign_send_request(self):
        
        self.ensure_one()
        responsible_count = len(set(self.sign_item_ids.mapped('responsible_id')))
        if responsible_count > 1:
            raise ValidationError(_('Users are not authorized to sign other users documents!'))
        context = {
            'sign_directly_without_mail': 1,
        }
        
        view_id = self.env.ref('sign.sign_send_request_view_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature Request'),
            'view_mode': 'form',
            'res_model': 'sign.send.request',
            'target': 'new',
            'context': context,
            'res_id': False,
            'views': [[view_id, 'form']],
        }
