# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

import time

class AllChannel(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = "all.channel"
    _description = "All Channel"
    _order = "id"

    is_add_all_channel = fields.Boolean(string="Is add all channel", default=False)
    # active = fields.Boolean(string="Active", default=True)

    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    company_id = fields.Many2one(related="partner_id.company_id")
    mail_channel_has_joined_ids = fields.Many2many(
        comodel_name="mail.channel",
        relation="mail_channel_has_joined_rel",
        column1="all_channel_id",
        column2="mail_channel_id")
    mail_channel_just_joined_ids = fields.Many2many(
        comodel_name="mail.channel",
        relation="mail_channel_just_joined_rel",
        column1="all_channel_id",
        column2="mail_channel_id")

    def action_create_partner_all_channel(self):
        vals = []
        all_channel_exists = self.env["all.channel"].search([])
        if not all_channel_exists:
            partner_ids = self.env["res.partner"].search([("user_ids", '!=', False)])
            # mail_channel_ids = self.env["mail.channel"].search([])
            for partner in partner_ids:
                vals.append({
                    "partner_id": partner.id,
                    # "mail_channel_has_joined_ids": [(6, 0, [mail_channel.id for mail_channel in mail_channel_ids if partner.id in mail_channel.channel_member_ids.mapped("partner_id.id")])]
                })
        self.create(vals)
        return True

    @api.model
    def action_sync_partner(self):
        vals = []
        partner_ids = self.env["res.partner"].search([("user_ids", '!=', False)]).filtered(lambda x: x.user_ids)
        all_channel = self.env["all.channel"].search([], order="id desc")
        partner_all_channel = self.env["all.channel"].search([]).mapped("partner_id.id")

        new_partner = [partner for partner in partner_ids if partner.id not in partner_all_channel]
        for partner in new_partner:
            vals.append({
                "partner_id": partner.id
            })
        self.create(vals)

        for channel in all_channel:
            if not channel.partner_id.user_ids:
                channel.unlink()
        return True

    @api.model
    def action_add_all_channel(self):
        time.sleep(3)
        is_not_add_all_channel = self.env["all.channel"].search([('is_add_all_channel', '=', False)])
        is_add_all_channel = self.env["all.channel"].search([('is_add_all_channel', '=', True)])

        mail_channel_ids = self.env["mail.channel"].search([("channel_type", "=", "channel")])
        for record in is_add_all_channel:
            mail_channel_has_joined_ids = mail_channel_ids.filtered(lambda x: record.partner_id.id in x.channel_member_ids.mapped("partner_id.id"))
            mail_channel_just_joined_ids = mail_channel_ids.filtered(lambda x: record.partner_id.id not in x.channel_member_ids.mapped("partner_id.id"))

            # faster
            if record.mail_channel_has_joined_ids and record.mail_channel_just_joined_ids:
                if record.mail_channel_has_joined_ids.ids.sort() == mail_channel_has_joined_ids.ids.sort():
                    if record.mail_channel_just_joined_ids.ids.sort() == mail_channel_just_joined_ids.ids.sort():
                        continue

            mail_channel_just_joined_ids.with_context(has_partner=record.partner_id)._subscribe_users(group_ids=False)

            record.update({
                "mail_channel_has_joined_ids": [(6, 0, mail_channel_has_joined_ids.ids)],
                "mail_channel_just_joined_ids": [(6, 0, mail_channel_just_joined_ids.ids)],
            })
        for record in is_not_add_all_channel:
            mail_channel_has_joined_ids = mail_channel_ids.filtered(lambda x: record.partner_id.id in x.channel_member_ids.mapped("partner_id.id"))

            new_mail_channel_has_joined_ids = mail_channel_has_joined_ids - record.mail_channel_just_joined_ids

            # faster
            if record.mail_channel_has_joined_ids and record.mail_channel_just_joined_ids and not record.mail_channel_just_joined_ids:
                if mail_channel_has_joined_ids.ids.sort() == new_mail_channel_has_joined_ids.ids.sort():
                    continue

            if record.mail_channel_just_joined_ids:
                user = self.env["res.users"].search([("partner_id", "=", record.partner_id.id)])
                record.mail_channel_just_joined_ids._remove_members(user)

            record.update({
                "mail_channel_has_joined_ids": [(6, 0, new_mail_channel_has_joined_ids.ids)],
                "mail_channel_just_joined_ids": [(5, 0, 0)],
            })
