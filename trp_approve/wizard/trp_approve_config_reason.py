# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import ast


class TrpApproveConfigReason(models.TransientModel):
    _name = 'trp.approve.config.reason'

    reason_id = fields.Many2one("trp.approve.reason", string="Lý do")
    reason = fields.Text(string="Mô tả")
    trp_approve_config_line_id = fields.Many2one('trp.approve.config.line', string="Cấu hình duyệt chi tiết")
    res_id = fields.Integer(string="Res ID")
    res_model = fields.Char(string="Res Model")
    type = fields.Selection([('refuse', 'Từ chối duyệt'), ('cancel', 'Hủy'), ('draft', 'Thiết lập về nháp')], default="refuse")
    approve_next_action = fields.Char('Hành động kế tiếp')

    def action_confirm(self):
        dict_refuse = {}
        record_id = self.env[self.res_model].browse(self.res_id)
        if self.type == "refuse":
            if not self.reason_id:
                raise ValidationError("Vui lòng chọn Lý do từ chối duyệt!")
            if self.trp_approve_config_line_id:
                res_history = self.env["trp.approve.history"].search(
                    [('res_model', '=', self.res_model), ('res_id', '=', self.res_id),
                     ('trp_approve_config_line_id', '=', self.trp_approve_config_line_id.id)], order='id desc')

                dict_history = {
                    'approve_user_id': self.env.user.id,
                    'approve_date': datetime.now(),
                    'reason_id': self.reason_id.id,
                    'reason': self.reason
                }

                res_history.write(dict_history)
                self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()
                if dict_history:
                    next_state = 'draft' if self.res_model in ('payment.request', 'payment.request.unc') else record_id.approve_state_init
                    dict_refuse = {
                        'trp_approve_config_line_id': False,
                        'trp_approve_reason_id': self.reason_id.id,
                        'trp_approve_reason_note': self.reason,
                        'approve_state_init': 'draft',
                        'state': next_state
                    }
                    if self.trp_approve_config_line_id.do_refuse:
                        dict_refuse.update(ast.literal_eval(self.trp_approve_config_line_id.do_refuse))
                    record_id.write(dict_refuse)
        else:
            dict_refuse = {
                'trp_approve_reason_id': self.reason_id.id,
                'trp_approve_reason_note': self.reason,
            }
            record_id.write(dict_refuse)

        if hasattr(record_id, 'message_post'):
            reason_name = self.reason_id.name if self.reason_id else ""
            note = self.reason if self.reason else ""
            if reason_name or note:
                action_name = "Từ chối duyệt"
                if self.type == "cancel":
                    action_name = "Hủy"
                elif self.type == "draft":
                    action_name = "Thiết lập về nháp"
                body = f"<b>{action_name}</b><br/>"
                if reason_name:
                    body += f"Lý do: {reason_name}<br/>"
                if note:
                    body += f"Ghi chú: {note}"
                record_id.message_post(body=body)

        if self.type != "refuse" and self.approve_next_action:
            return getattr(record_id.with_context(**self.env.context), self.approve_next_action)()

        return dict_refuse
