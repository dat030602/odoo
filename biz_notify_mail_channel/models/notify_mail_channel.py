# -*- coding: utf-8 -*-


from odoo import models, fields, api
from datetime import datetime, timedelta

MUTE_NOTIFY_TYPE = {
    "1_hour": 3600,
    "4_hours": 14400,
    "12_hours": 43200,
    "24_hours": 86400,
}


class NotifyMailChannel(models.Model):
    _name = "notify.mail.channel"
    _description = "Table Notify Mail Channel"

    active = fields.Boolean(string="Active", default=True)
    notify_datetime = fields.Datetime(string="Notify Datetime")
    mute_notify_type = fields.Selection(selection=[
        ("1_hour", "For 1 hour"),
        ("4_hours", "For 4 hours"),
        ("12_hours", "For 12 hours"),
        ("24_hours", "For 24 hours"),
        ("until_turn_on", "Until turn on")
    ], string="Mute Notify Type", default=False, copy=False)
    mail_channel_id = fields.Many2one(comodel_name="mail.channel", string="Mail Channel")
    user_id = fields.Many2one(comodel_name="res.users", string="User")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner", related="user_id.partner_id")

    def get_mute_notify_mail_channel(self):
        vals = {}
        if not self:
            return vals
        if self.mute_notify_type not in ["until_turn_on"]:
            now = fields.Datetime.now()
            if now > self.notify_datetime:
                self.update({"active": False})
                vals.update({"is_mute_notify": False, "mute_notify_type": False})
            else:
                vals.update({"is_mute_notify": True, "mute_notify_type": self.mute_notify_type})
        else:
            vals.update({"is_mute_notify": True, "mute_notify_type": self.mute_notify_type})
        return vals

    def action_mute_notify_mail_channel(self, user_id=None, channel_id=None, mute_notify_type=None):
        if not user_id or not channel_id:
            return True
        vals = {}
        if mute_notify_type:
            if mute_notify_type not in ["until_turn_on"]:
                notify_datetime = datetime.utcnow() + timedelta(seconds=MUTE_NOTIFY_TYPE.get(mute_notify_type))
                vals.update({
                    "notify_datetime": notify_datetime
                })
            vals.update({
                "user_id": user_id,
                "mail_channel_id": channel_id,
                "mute_notify_type": mute_notify_type,
            })
            notify_id = self.create(vals)
            self.env['bus.bus']._sendone(notify_id.partner_id, "mail.thread/insert",
                                         {"id": notify_id.mail_channel_id.id, "model": "mail.channel", "isMuteNotify": True})
        else:
            record = self.search([
                ("user_id", "=", user_id),
                ("mail_channel_id", "=", channel_id),
                ("active", "=", True)
            ], limit=1)
            if record:
                self.env['bus.bus']._sendone(record.partner_id, "mail.thread/insert", {"id": record.mail_channel_id.id, "model": "mail.channel", "isMuteNotify": False})
                record.update({"active": False})
        return True



