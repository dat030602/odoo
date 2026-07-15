# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class SendSMS(models.TransientModel):
    _inherit = "sms.composer"

    # Inherit
    # template_id = fields.Many2one(domain="['|', ('model', '=', res_model), ('fpt_template_type', '=', 'happy_birthday')]")

    def action_send_sms(self):
        if self.template_id and self.template_id.fpt_template_type:
            sms_fpt = self.env["bizapps.fpt.sms"].action_check_had_sent_sms_birthday(phone=self.recipient_single_number_itf)
            if sms_fpt:
                raise UserError(_("Happy birthday messages have been sent. Please check again"))

            fpt_template = self.template_id
            record = self.env[self.res_model].browse(self.res_id)
            if fpt_template and record:
                phone = self.recipient_single_number_itf
                body = self.body
                sms = self.env['bizapps.fpt.sms'].sudo().sent_sms_api(phone, body)
                if sms:
                    sms.update({"is_happy_birthday_sms_fpt": True})

        else:
            super(SendSMS, self).action_send_sms()
