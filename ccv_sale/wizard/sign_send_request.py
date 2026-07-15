# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SignSendRequest(models.TransientModel):
    _inherit = 'sign.send.request'

    @api.model
    def default_get(self, fields_list):
        """Override default_get để tự động sắp xếp mail_sent_order theo thứ tự signer_ids"""
        res = super(SignSendRequest, self).default_get(fields_list)

        res['refusal_allowed'] = True
        
        # Chỉ update mail_sent_order nếu có signer_ids và template_id
        if res.get('signer_ids') and res.get('template_id'):
            # Lấy thứ tự hiện tại và update mail_sent_order theo thứ tự
            for index, signer_data in enumerate(res['signer_ids'], 1):
                if len(signer_data) >= 3:  # Đảm bảo có đủ (0, 0, {...})
                    signer_data[2]['mail_sent_order'] = index
        
        return res

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Override _onchange_template_id để tự động sắp xếp mail_sent_order theo thứ tự signer_ids"""
        # Gọi super để lấy logic gốc
        super(SignSendRequest, self)._onchange_template_id()
        
        # Update mail_sent_order theo thứ tự hiện tại của signer_ids
        if self.signer_ids:
            for index, signer in enumerate(self.signer_ids, 1):
                signer.mail_sent_order = index
