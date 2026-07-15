# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Channel(models.Model):
    _inherit = "mail.channel"

    def channel_info(self):
        channel_infos = super(Channel, self).channel_info()
        for channel_info in channel_infos:
            channel_id = self.sudo().browse(int(channel_info.get("id"))).exists()
            if channel_id:
                vals = {}
                notify_id = self.env["notify.mail.channel"].search([
                    ("user_id", "=", self._uid),
                    ("mail_channel_id", "=", channel_id.id),
                    ("active", "=", True)
                ], limit=1)
                if notify_id:
                    vals = notify_id.get_mute_notify_mail_channel()
                channel_info.update(vals)
        return channel_infos

    def _notify_thread_by_ocn(self, message, recipients_data, msg_vals=False, **kwargs):
        channels = self.filtered(lambda channel: channel.channel_type in ["group", "channel"])
        if channels:
            channel_rdata = recipients_data.copy()
            channel_rdata += [{
                'id': partner.id,
                'share': partner.partner_share,
                'active': partner.active,
                'notif': 'ocn',
                'type': 'customer',
                'groups': [],
            } for partner in channels.mapped("channel_partner_ids")]
        else:
            channel_rdata = recipients_data
        return super(Channel, self)._notify_thread_by_ocn(message, channel_rdata, msg_vals=msg_vals, **kwargs)
