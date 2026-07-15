# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class SignRequests(models.Model):
    _name = 'sign.requests'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _description = 'Sign Requests'
    _order = 'date desc, state'


    name = fields.Char(string="Tên", required=True, copy=False, readonly=True)
    date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self), string="Ngày")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string="Công ty")
    
    partner_id = fields.Many2one("res.partner", string="Đối tác")
    user_id = fields.Many2one("res.users", string="Người tạo", default=lambda self: self.env.user)
    
    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')], 
        'Trạng thái', default="draft", tracking=True)
    note = fields.Text("Ghi chú")
    trp_approve_history_ids = fields.One2many('trp.approve.history', 'sign_requests_id', string='Lịch sử duyệt', copy=False)
    
    # Các field tiền tệ chung
    amount_untax_total = fields.Monetary("Tổng chưa thuế")
    amount_tax_total = fields.Monetary("Tổng thuế")
    amount_total = fields.Monetary("Tổng cộng")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ')
    tax_totals = fields.Binary(exportable=False)

    def unlink(self):
        for record in self:
            if record.state not in ['refuse', 'cancel','draft']:
                raise UserError("Không thể xóa yêu cầu ký đã duyệt!")
        return super(SignRequests, self).unlink()

    def action_cancel(self):
        self.write({
            'state': 'cancel'
        })
        res_history = self.trp_approve_history_ids
        self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()

    def action_confirm(self):
        self = self.sudo()
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('draft'):
            self.approve_next_action = 'action_confirm'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()

        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'approve':
                self.update({
                    'state': 'approved',
                })
                return


    def action_undo(self):
        self.write({
            'state': 'draft'
        })

    @api.model
    def create_default_approve_config(self):
        approve_id = self.env['trp.approve.config'].search([('model_id.model', '=', self._name)])
        if not approve_id:
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            user_ids = [2]
            self.env['trp.approve.config'].create({
                'model_id': model_id.id,
                'trp_approve_config_line_ids': [
                    (0, 0, {
                        'level': 1,
                        'manager_type': 'manager',
                        'user_ids': user_ids,
                        'type': 'new',
                    }),
                    (0, 0, {
                        'level': 1,
                        'manager_type': 'manager',
                        'user_ids': user_ids,
                        'type': 'cancel',
                    })]
            })
