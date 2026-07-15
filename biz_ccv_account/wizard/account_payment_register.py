# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import frozendict
from datetime import datetime

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'


    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)

        move = False
        if self._context.get('active_model') == 'account.move':
            move = self.env['account.move'].browse(self._context.get('active_ids', []))
        elif self._context.get('active_model') == 'account.move.line':
            move = self.env['account.move.line'].browse(self._context.get('active_ids', [])).mapped("move_id")

        if move:
            if move[0].move_type == 'in_invoice':
                res['payment_date'] = move[0].document_date or datetime.now()
                communication = [move[0].name]
                if move[0].note:
                    communication.append(move[0].note)

                res['communication'] = ' - '.join(communication)

        return res
