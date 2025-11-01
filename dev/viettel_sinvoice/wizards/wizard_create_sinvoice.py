# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CreateSInvoiceWizard(models.TransientModel):
    _name = 'wizard.create.sinvoice'
    _description = 'Remake the sequence of Journal Entries.'

    move_ids = fields.Many2many('account.move')

    @api.model
    def default_get(self, fields_list):
        values = super(CreateSInvoiceWizard, self).default_get(fields_list)
        active_move_ids = self.env['account.move']
        if self.env.context['active_model'] == 'account.move' and 'active_ids' in self.env.context:
            active_move_ids = self.env['account.move'].browse(self.env.context['active_ids'])
        if not len(active_move_ids) > 1:
            raise UserError('Tính năng này chỉ sử dụng để gộp nhiều Công nợ!')
        values['move_ids'] = [(6, 0, active_move_ids.ids)]
        return values

    def action_create_sinoice(self):
        self.move_ids.action_create_data_sinvoice()
