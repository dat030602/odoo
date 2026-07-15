from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from reportlab.rl_config import TTFSearchPath

TTFSearchPath.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "static", "fonts"))
        
class SignRequest(models.Model):
    _inherit = 'sign.request'
    _description = "Signature Request"


    def unlink(self):
        current_user = self.env.user
        if not current_user.has_group('sign.group_sign_manager') and not current_user.has_group('base.group_system'):
            raise ValidationError(_('User is not allowed to delete signed document. Please contact admin support system !'))
                                            
        return super(SignRequest, self).unlink()

    def _get_font(self):
        custom_font = super(SignRequest, self)._get_font()
        
        if custom_font:
            pdfmetrics.registerFont(TTFont(custom_font, custom_font + ".ttf"))
        
        return custom_font



class SignRequestItem(models.Model):
    _inherit = 'sign.request.item'
    _description = "Signature Request Item"


    def _default_partner_id(self):
        partner_ids = self.env['res.users'].search([('partner_id','!=',False)]).mapped('partner_id')
        return [('user_ids','!=',False)]


    partner_id = fields.Many2one(domain=lambda self: self._default_partner_id())

