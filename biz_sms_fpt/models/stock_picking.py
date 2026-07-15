# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if isinstance(res, bool) and res:
            if self.sale_id and self.location_dest_id.usage == 'customer':
                check_qty = False
                for line in self.sale_id.order_line:
                    if line.qty_delivered < line.product_uom_qty:
                        check_qty = True
                        break
                if not check_qty or self.product_id.type not in [
                    'service'] and not self.sale_id.is_sent_completion_sms_fpt:
                    self = self.sudo()
                    fpt_template = self.env['sms.template'].search([
                        ("fpt_template_type", "=", "order_completion"),
                        ("model", "=", "stock.picking")
                    ], limit=1)
                    partner_id = self.sale_id.partner_id
                    if fpt_template and partner_id:
                        phone = partner_id.phone or partner_id.mobile
                        body = fpt_template._render_field('body', self.ids, set_lang=partner_id.lang or 'vi_VN')[
                            self.id]
                        sms = self.env['bizapps.fpt.sms'].sudo().sent_sms_api(phone, body)
                        if sms:
                            sms.update({"is_order_completion_sms_fpt": True})
                        self.sale_id.update({"is_sent_completion_sms_fpt": True})
        return res
