# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ViettelSinvoiceData(models.TransientModel):
    _name = 'viettel.sinvoice.cancel'
    _description = "Sinvoice cancel"

    def _compute_additionalReferenceDesc(self):
        return self.env['ir.sequence'].next_by_code('sinvoice.reference')

    additionalReferenceDate = fields.Datetime(required=True)
    additionalReferenceDesc = fields.Char('Additional Reference Desc', default=_compute_additionalReferenceDesc)
    reason = fields.Char(required=True)

    def do_cancel(self):
        active_model = self._context.get('active_model')
        active_model_id = self.env[active_model].browse(self._context.get('active_id'))
        if active_model_id:
            data = {
                'additionalReferenceDesc': self.additionalReferenceDesc,
                'str_additionalReferenceDate': int(self.additionalReferenceDate.timestamp()),
                'additionalReferenceDate': self.additionalReferenceDate,
                'reason': self.reason,
            }
            active_model_id.action_cancel_sinvoice(data)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
