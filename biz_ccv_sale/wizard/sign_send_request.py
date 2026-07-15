# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class SignSendRequest(models.TransientModel):
    _inherit = 'sign.send.request'

    sale_order_id = fields.Many2one(comodel_name='sale.order',
                                    string='Sale Order ID',
                                    ondelete='cascade',
                                    domain=[('sign_request_id', 'in', [False])])

    def send_request(self):
        if self.sale_order_id:
            request = self.create_request()
            if request:
                self.sale_order_id.update({'sign_request_id': request.id})
                request.update({'sale_order_id': self.sale_order_id.id})
            if self.activity_id:
                self._activity_done()
                return {'type': 'ir.actions.act_window_close'}
            return request.go_to_document()
        return super(SignSendRequest, self).send_request()
