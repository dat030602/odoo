# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_sent_confirmation_sms_fpt = fields.Boolean(string="Order confirmation sent", copy=False)
    is_sent_completion_sms_fpt = fields.Boolean(string="Completed order sent", copy=False)

    def action_confirm(self):
        rec = super(SaleOrder, self).action_confirm()
        if self.state in ["sale", "done"] and not self.is_sent_confirmation_sms_fpt:
            self = self.sudo()
            fpt_template = self.env['sms.template'].search([
                ("fpt_template_type", "=", "order_confirmation"),
                ("model", "=", "sale.order")
            ], limit=1)
            partner_id = self.partner_id
            if fpt_template and partner_id:
                phone = partner_id.phone or partner_id.mobile
                body = fpt_template._render_field('body', self.ids, set_lang=partner_id.lang or 'vi_VN')[self.id]
                sms = self.env['bizapps.fpt.sms'].sudo().sent_sms_api(phone, body)
                if sms:
                    sms.update({"is_order_confirmation_sms_fpt": True})
                self.update({"is_sent_confirmation_sms_fpt": True})
        return rec
