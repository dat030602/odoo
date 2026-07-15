# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, http, _, Command
from odoo.exceptions import UserError

class SignRequest(models.Model):
    _inherit = "sign.request"

    def go_to_signable_document(self, request_items=None):
        if not request_items:
            sign_request_items_sent = self.request_item_ids.filtered(lambda sri: sri.state == 'sent')
            smallest_order = min(sign_request_items_sent.mapped('mail_sent_order'))
            next_request_items = sign_request_items_sent.filtered(lambda sri: sri.mail_sent_order == smallest_order)
            request_items = self.request_item_ids.filtered(lambda r: not r.partner_id or (r.state == 'sent' and r.partner_id.id == self.env.user.partner_id.id))
            if not request_items:
                return
            elif not next_request_items:
                pass
            elif len(next_request_items) < 2 and request_items[:1].id != next_request_items.id:
                raise UserError(_("You have not yet signed the document, need to wait for '%s' to sign first.") % next_request_items.partner_id.name)

        return super(SignRequest, self).go_to_signable_document(request_items)


class SignRequestItem(models.Model):
    _inherit = "sign.request.item"

    # Inherit
    mail_sent_order = fields.Integer(string="Sequence", default=1)

    def write(self, vals):
        old = {}
        if 'mail_sent_order' in vals:
            for sign in self:
                old[sign.id] = sign.mail_sent_order
                
        check_mail_sent = self._context.get('check_mail_sent', False)
        if vals.get('partner_id'):
            old_sign_partner = self.partner_id.id
            check_mail_sent = self.is_mail_sent

        res = super(SignRequestItem, self.with_context(check_mail_sent=check_mail_sent)).write(vals)

        request_items_reassigned = self.env['sign.request.item']
        if vals.get('partner_id'):
            request_items_reassigned |= self.filtered(lambda sri: sri.partner_id.id != old_sign_partner)
            for request_item in request_items_reassigned:
                new_sign_user = request_item.partner_id.user_ids[:1]
                # Remove activity create when change partner
                request_item.sign_request_id.activity_unlink(['mail.mail_activity_data_todo'], user_id=new_sign_user.id)
                if check_mail_sent:
                    # Auto send mail and create activity
                    request_item.send_signature_accesses()

        if 'mail_sent_order' in vals:
            for sign in self:
                message = _('User %s đã chỉnh sửa thứ tự Signer %s: %s -> %s') % (self.env.user.name, sign.partner_id.name, old[sign.id], sign.mail_sent_order)
                sign.sign_request_id.message_post(body=message)
        return res


