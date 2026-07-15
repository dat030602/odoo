from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
        
class SignSendRequest(models.TransientModel):
    _inherit = 'sign.send.request'

    def _default_partner_id(self):
        partner_ids = self.env['res.users'].search([('partner_id','!=',False)]).mapped('partner_id')
        return [('id','in', partner_ids.ids)]

    signer_id = fields.Many2one(domain=lambda self: self._default_partner_id())


    @api.onchange('template_id')
    def _onchange_template_id(self):
        ctx = dict(self._context)
        
        if 'sign_directly_without_mail' in ctx and ctx['sign_directly_without_mail'] == 1: 
            responsible_count = len(set(self.template_id.sign_item_ids.mapped('responsible_id')))
            if responsible_count > 1:
                raise ValidationError(_('Users are not authorized to sign other users documents!'))
        
        super(SignSendRequest, self)._onchange_template_id()


class SignSendRequestSigner(models.TransientModel):
    _inherit = "sign.send.request.signer"
    _description = 'Sign send request signer'

    def _default_partner_id(self):
        # ctx = dict(self._context)
        # partner_ids = self.env['res.users'].search([('partner_id','!=',False)]).mapped('partner_id')
        # domain = [('id','in', partner_ids.ids)]
        # if 'sign_directly_without_mail' in ctx and ctx['sign_directly_without_mail'] == 1:
        #     domain += [('id','in',self.env.user.partner_id.ids)]

        return []

    partner_id = fields.Many2one(domain=lambda self: self._default_partner_id())
   



