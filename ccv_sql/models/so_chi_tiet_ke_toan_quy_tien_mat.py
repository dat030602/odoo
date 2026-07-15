# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class CcvSoChiTietKeToanQuyTienMat(models.Model):
    _name = 'ccv.so.chi.tiet.ke.toan.quy.tien.mat'
    _description = 'Sổ Kế Toán Chi Tiết Quỹ Tiền Mặt'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string="Tên", default="Sổ Kế Toán Chi Tiết Quỹ Tiền Mặt", tracking=True)
    date_from = fields.Date(string="Từ ngày", default=lambda s: date.today().replace(day=1), required=True)
    date_to = fields.Date(string="Đến ngày", default=lambda s: date.today(), required=True)
    account_id = fields.Many2one("account.account", string="Tài khoản", required=True)
    page_break = fields.Boolean(string="Xuống dòng khi in", default=False)

    voter_id = fields.Many2one("res.users", string="Người lập phiếu", default=lambda s: s.env.user)
    cashier_id = fields.Many2one("res.users", string="Thủ quỹ")
    cash_chief_acc_id = fields.Many2one("res.users", string="Kế toán trưởng")
    cash_unit_heads_id = fields.Many2one("res.users", string="Thủ trưởng đơn vị")

    line_ids = fields.One2many('ccv.so.chi.tiet.ke.toan.quy.tien.mat.line', 'parent_id', string="Chi tiết")

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'),
         ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        string='Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many(
        'trp.approve.history', 'ccv_so_chi_tiet_ke_toan_quy_tien_mat_id',
        string='Lịch sử duyệt', copy=False)

    bld_approved_user_id = fields.Many2one(
        'res.users', string='Người dự BLD đã duyệt',
        compute='_compute_bld_approved_user', store=True)

    @api.depends('trp_approve_history_ids', 'trp_approve_history_ids.approve_user_id',
                 'trp_approve_history_ids.trp_approve_config_line_id')
    def _compute_bld_approved_user(self):
        for rec in self:
            histories_with_level = rec.trp_approve_history_ids.filtered(
                lambda h: h.trp_approve_config_line_id and h.trp_approve_config_line_id.level
            )
            if histories_with_level:
                max_level = max(histories_with_level.mapped('trp_approve_config_line_id.level'))
                last_level_history = histories_with_level.filtered(
                    lambda h: h.trp_approve_config_line_id.level == max_level and h.approve_user_id
                )
                if last_level_history:
                    rec.bld_approved_user_id = last_level_history[0].approve_user_id
                else:
                    rec.bld_approved_user_id = rec.cash_unit_heads_id
            else:
                rec.bld_approved_user_id = rec.cash_unit_heads_id

    is_user_current = fields.Boolean(compute='_compute_is_user_current')

    @api.depends('current_approve_user_ids')
    def _compute_is_user_current(self):
        for rec in self:
            rec.is_user_current = self.env.user in rec.current_approve_user_ids

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        account = self.env['account.account'].search([('code', '=', '11111')], limit=1)
        defaults.update({
            'voter_id': self.env.user.id,
            'cashier_id': int(env_params.get_param('ccv_sql.cashier_id', 0)),
            'cash_chief_acc_id': int(env_params.get_param('ccv_sql.cash_chief_acc_id', 0)),
            'cash_unit_heads_id': int(env_params.get_param('ccv_sql.cash_unit_heads_id', 0)),
            'account_id': account.id if account else False,
        })
        return defaults

    def action_confirm(self):
        self.ensure_one()
        # Proxy to alpha.report to reuse the PostgreSQL logic
        proxy = self.env['alpha.report'].create({
            'type': 'so_chi_tiet_ke_toan_quy_tien_mat',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'account_id': self.account_id.id,
        })
        # Clear ORM cache so that the newly created proxy doesn't cache an empty line4_ids list
        self.env.invalidate_all()
        
        # Execute the SQL logic which inserts into alpha_report_line4 via raw SQL
        proxy.report_so_chi_tiet_ke_toan_quy_tien_mat()
        
        # Raw SQL inserts bypass the ORM cache. We must query them directly.
        self.env.invalidate_all()
        proxy_lines = self.env['alpha.report.line4'].search([('parent_id', '=', proxy.id)])
        
        # Build lines from proxy_lines
        lines_data = []
        for l in proxy_lines:
            lines_data.append((0, 0, {
                'date': l.date,
                'account_move_id': l.move_id.id if l.move_id else False,
                'account_move2_id': l.move2_id.id if l.move2_id else False,
                'note': l.note,
                'account_dest_id': l.account_dest_id.id if l.account_dest_id else False,
                'debit': l.debit,
                'credit': l.credit,
                'end_debit': l.end_debit,
                'partner_id': l.partner_id.id if l.partner_id else False,
            }))
        
        self.line_ids.unlink()
        self.write({'line_ids': lines_data})
        # Cleanup the proxy
        proxy.unlink()

    def action_print_pdf_report(self):
        return self.env.ref('ccv_sql.ccv_so_chi_tiet_ke_toan_quy_tien_mat_new_report').report_action(self)

    def convert_vnd(self, amount):
        a = format(amount, ',.0f')
        return a

    def convert_print(self, value):
        if str(value).find('202') > -1:
            return str(value).split('-')[2] + '/' + str(value).split('-')[1] + '/' + str(value).split('-')[0]
        return value

    def action_sign(self):
        self = self.sudo()
        if not self.line_ids:
            raise ValidationError(_("Vui lòng lấy dữ liệu trước khi trình duyệt!"))
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state == 'draft':
            self.approve_next_action = 'action_sign'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()
        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'approve':
                self.update({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
        res_history = self.trp_approve_history_ids
        self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]) \
            .with_context(skip_approve_done=True).action_done()

    def action_undo(self):
        self.write({'state': 'draft'})

class CcvSoChiTietKeToanQuyTienMatLine(models.Model):
    _name = 'ccv.so.chi.tiet.ke.toan.quy.tien.mat.line'
    _description = 'Chi tiết Sổ kế toán quỹ tiền mặt'

    parent_id = fields.Many2one('ccv.so.chi.tiet.ke.toan.quy.tien.mat', ondelete='cascade')
    date = fields.Date(string="Ngày chứng từ")
    account_move_id = fields.Many2one('account.move', string="Số phiếu thu")
    account_move2_id = fields.Many2one('account.move', string="Số phiếu chi")
    note = fields.Char(string="Diễn giải")
    account_dest_id = fields.Many2one('account.account', string="TK đối ứng")
    debit = fields.Float(string="PS nợ")
    credit = fields.Float(string="PS có")
    end_debit = fields.Float(string="Số tồn")
    partner_id = fields.Many2one('res.partner', string="Người nhận/ người nộp")

    def read(self, fields=None, load='_classic_read'):
        res = super(CcvSoChiTietKeToanQuyTienMatLine, self).read(fields, load)
        for record in res:
            if 'account_move_id' in record and record['account_move_id']:
                move_id = record['account_move_id'][0]
                move = self.env['account.move'].browse(move_id)
                if move.exists():
                    record['account_move_id'] = (move_id, move.name or '')
            if 'account_move2_id' in record and record['account_move2_id']:
                move2_id = record['account_move2_id'][0]
                move2 = self.env['account.move'].browse(move2_id)
                if move2.exists():
                    record['account_move2_id'] = (move2_id, move2.name or '')
        return res
