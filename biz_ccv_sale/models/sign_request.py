# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools


class SignRequest(models.Model):
    _inherit = 'sign.request'

    sale_order_id = fields.Many2one(comodel_name='sale.order',
                                    string='Sale Order ID',
                                    ondelete='cascade',
                                    domain=[('sign_request_id', 'in', [False])])

    def write(self, vals):
        res = super(SignRequest, self).write(vals)
        if 'sale_order_id' in vals:
            for record in self:
                if record.sale_order_id and not record.sale_order_id.sign_request_id:
                    record.sale_order_id.update({'sign_request_id': record.id})
        return res
