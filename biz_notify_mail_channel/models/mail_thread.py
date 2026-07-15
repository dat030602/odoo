# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # Inherit
    def _notify_thread_by_ocn(self, message, recipients_data, msg_vals=False, **kwargs):
        vals = []
        if self and self._name == "mail.channel":
            icp_sudo = self.env['ir.config_parameter'].sudo()
            # Avoid to send notification if this feature is disabled or if no user use the mobile app.
            if not icp_sudo.get_param('odoo_ocn.project_id') or not icp_sudo.get_param('mail_mobile.enable_ocn'):
                return

            notif_pids = [r['id'] for r in recipients_data if r['active']]
            no_inbox_pids = [r['id'] for r in recipients_data if r['active'] and r['notif'] != 'inbox']

            if not notif_pids:
                return

            msg_vals = dict(msg_vals or {})
            msg_sudo = message.sudo()
            msg_type = msg_vals.get('message_type') or msg_sudo.message_type
            author_id = [msg_vals.get('author_id')] if 'author_id' in msg_vals else msg_sudo.author_id.ids

            # never send to author and to people outside of odoo (email), except comments
            if msg_type == 'comment':
                pids = set(notif_pids) - set(author_id)
                for pid in list(pids):
                    notify_id = self.env["notify.mail.channel"].search([
                        ("partner_id", "=", pid),
                        ("mail_channel_id", "=", self.id),
                        ("active", "=", True)
                    ], limit=1)
                    if notify_id:
                        vals.append(notify_id.partner_id.id)
                pids -= set(vals)
                self._notify_by_ocn_send(message, list(pids), msg_vals=msg_vals)
            elif msg_type in ('notification', 'user_notification', 'email'):
                pids = (set(notif_pids) - set(author_id) - set(no_inbox_pids))
                self._notify_by_ocn_send(message, list(pids), msg_vals=msg_vals)
        else:
            return super(MailThread, self)._notify_thread_by_ocn(message, recipients_data, msg_vals=False, **kwargs)
