# -*- coding: utf-8 -*-

from odoo import fields, models, api


class Channel(models.Model):
    _inherit = "mail.channel"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        rdata = super(Channel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)

        if self.channel_type == "channel":
            bus_notifications = []
            for member in self.channel_member_ids.filtered("partner_id"):
                bus_notifications.insert(0, [member.partner_id, "mail.channel/last_interest_dt_changed", {
                    "id": self.id,
                    "isServerPinned": member.is_pinned,
                    "last_interest_dt": member.last_interest_dt,
                }])
            self.env["bus.bus"].sudo()._sendmany(bus_notifications)
        return rdata

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *, message_type="notification", **kwargs):
        self.filtered(lambda channel: channel.channel_type == "channel").mapped("channel_member_ids").sudo().write({
            "is_pinned": True,
            "last_interest_dt": fields.Datetime.now(),
        })
        return super(Channel, self.with_context(mail_create_nosubscribe=True, mail_post_autofollow=False)).message_post(message_type=message_type, **kwargs)