# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignSendRequest(models.TransientModel):
    _inherit = 'sign.send.request'

    def default_get(self, fields):
        res = super(SignSendRequest, self).default_get(fields)
        if not res.get('template_id'):
            return res
        if 'signers_count' in res and res['signers_count'] >= 2:
            res['set_sign_order'] = True
        return res

    # Inherit
    set_sign_order = fields.Boolean(string="Specify Signing Order", help="Signatures will be requested from lowest order to highest order.", readonly=True)