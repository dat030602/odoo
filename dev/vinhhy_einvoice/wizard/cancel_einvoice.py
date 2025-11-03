# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CancelEInvoice(models.TransientModel):
    _name = 'cancel.einvoice'
    _description = 'Cancel E-Invoice'

    reason_adjust_einv = fields.Char(string='Reason Cancel')
    seller_responsible = fields.Many2one('res.users')
    seller_position = fields.Char(string='Seller Position')
    buyer_responsible = fields.Many2one('res.partner')
    buyer_position = fields.Char(string='Buyer Position')
    vh_inv_id = fields.Many2one('vinhhy.einvoice', string='Vinh Hy E-Invoice')

    @api.model
    def default_get(self, fields_list):
        res = super(CancelEInvoice, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        vh_inv = self.env['vinhhy.einvoice'].browse(active_id)
        if vh_inv:
            res.update({
                'vh_inv_id': active_id,
                'seller_responsible': vh_inv.user_id.id if vh_inv.user_id else False,
                'seller_position': vh_inv.user_id.partner_id.function if vh_inv.user_id else '',
                'buyer_responsible': vh_inv.partner_id.id if vh_inv.partner_id else False,
                'buyer_position': vh_inv.partner_id.function if vh_inv.partner_id else ''
            })
        return res

    def action_cancel_inv(self):
        self.vh_inv_id.with_context(reason_adjust_einv=self.reason_adjust_einv,seller_responsible=self.seller_responsible.id, seller_position=self.seller_position, 
            buyer_responsible= self.buyer_responsible.id, buyer_position= self.buyer_position).action_vh_einv_cancel()