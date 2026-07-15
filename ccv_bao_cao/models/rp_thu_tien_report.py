# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class RpThuTienReport(models.Model):
    _name = 'rp.thu.tien.report'
    _description = 'Báo cáo thu tiền phòng kinh doanh'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string="Tên", default="Báo cáo thu tiền phòng kinh doanh",
                       tracking=True, required=True)
    date_from = fields.Date(string="Từ ngày", default=lambda s: date.today(), required=True)
    date_to = fields.Date(string="Đến ngày", default=lambda s: date.today(), required=True)
    team_ids = fields.Many2many('crm.team', string='Phòng kinh doanh',
                                help="Chọn các phòng kinh doanh. Để trống để lấy tất cả.")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ',
                                  default=lambda s: s.env.ref('base.VND', raise_if_not_found=False))

    # Người ký
    voter_id = fields.Many2one('res.users', string='Người Lập Biểu',
                               default=lambda s: s.env.user)
    sales_chief_id = fields.Many2one('res.users', string='Kế toán công nợ')
    chief_acc_id = fields.Many2one('res.users', string='Kế Toán Trưởng')
    unit_heads_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')

    line_ids = fields.One2many('rp.thu.tien.report.line', 'parent_id', string="Chi tiết")

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'),
         ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        string='Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many(
        'trp.approve.history', 'rp_thu_tien_report_id',
        string='Lịch sử duyệt', copy=False)

    is_user_current = fields.Boolean(compute='_compute_is_user_current')

    @api.depends('current_approve_user_ids')
    def _compute_is_user_current(self):
        for rec in self:
            rec.is_user_current = self.env.user in rec.current_approve_user_ids

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', 'trp_approve_config_line_id.job_ids',
                 'sales_chief_id')
    def _compute_current_approve_users(self):
        super()._compute_current_approve_users()
        for record in self:
            cfg = record.trp_approve_config_line_id
            if cfg and cfg.manager_type == 'sales_chief':
                chief = record.sales_chief_id
                approver_ids = chief.ids if chief else []
                if cfg.user_ids:
                    approver_ids += cfg.user_ids.ids
                for job in cfg.job_ids:
                    approver_ids += job.employee_ids.mapped('user_id').ids
                if record.delegate_approver_ids:
                    approver_ids += record.delegate_approver_ids.ids
                record.current_approve_user_ids = [(6, 0, list(set(approver_ids)))]

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        sales_chief_id = env_params.get_param('ccv_bao_cao.sales_chief_id', False)
        chief_acc_param_id = env_params.get_param('ccv_bao_cao.chief_acc_id', False)
        defaults.update({
            'voter_id': self.env.user.id,
            'sales_chief_id': int(sales_chief_id) if sales_chief_id else False,
            'chief_acc_id': int(chief_acc_param_id) if chief_acc_param_id else False,
            'unit_heads_id': int(director_id) if director_id else False,
        })
        return defaults

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise ValidationError(_("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày'."))

    @api.onchange('team_ids')
    def _onchange_team_ids(self):
        pass

    @api.onchange('date_from', 'date_to')
    def _onchange_date_range(self):
        for rec in self:
            rec._update_name()

    def _update_name(self):
        self.ensure_one()
        parts = ["Báo cáo thu tiền khối kinh doanh"]
        if self.team_ids:
            names = self.team_ids.mapped('name')
            parts.append(", ".join(names))
        if self.date_from and self.date_to:
            if self.date_from == self.date_to:
                parts.append(self.date_from.strftime('%d/%m/%Y'))
            else:
                parts.append("%s - %s" % (
                    self.date_from.strftime('%d/%m/%Y'),
                    self.date_to.strftime('%d/%m/%Y'),
                ))
        elif self.date_from:
            parts.append(self.date_from.strftime('%d/%m/%Y'))
        self.name = " - ".join(parts)

    def unlink(self):
        for record in self:
            if not self.env.user.has_group('base.group_system') and record.state not in ('draft', 'refuse', 'cancel'):
                raise UserError(_("Không thể xóa phiếu đã/đang duyệt!"))
        return super().unlink()

    # ------------------------------------------------------------
    # Quy trình duyệt
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # Hành động lấy dữ liệu
    # ------------------------------------------------------------
    def action_confirm(self):
        """Lấy dữ liệu phiếu thu của phòng kinh doanh từ account.payment."""
        self.ensure_one()
        if self.state not in ('draft',):
            raise UserError(_("Chỉ có thể lấy dữ liệu khi phiếu ở trạng thái Nháp."))
        self.line_ids.unlink()

        Payment = self.env['account.payment'].sudo()
        domain = [
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.currency_id:
            domain.append(('currency_id', '=', self.currency_id.id))
        payments = Payment.search(domain).sorted(lambda p: (p.date, p.id))

        if self.team_ids:
            payments = payments.filtered(lambda p: p.partner_id.team_id in self.team_ids)

        Line = self.env['rp.thu.tien.report.line'].sudo()
        count = 0
        for pay in payments:
            count += 1
            move = pay.move_id
            # Lấy tên PKD từ team_ids của báo cáo
            pkd_name = ''
            if pay.partner_id.team_id and pay.partner_id.team_id.id in self.team_ids.ids:
                pkd_name = pay.partner_id.team_id.name if pay.partner_id.team_id.name else ''
            
            Line.create({
                'parent_id': self.id,
                'no': count,
                'date': pay.date,
                'partner_id': pay.partner_id.id,
                'partner_code': pay.partner_id.code_contact or '',
                'partner_name': pay.partner_id.name or '',
                'reference': pay.ref or (move.ref if move else '') or '',
                'note': pay.name or '',
                'amount': pay.amount,
                'currency_id': pay.currency_id.id,
                'payment_id': pay.id,
                'move_id': move.id if move else False,
                'pkd_sign': pkd_name,
            })

    def action_view_tree(self):
        self.ensure_one()
        return {
            'name': _("Chi tiết Báo cáo thu tiền PKD"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'rp.thu.tien.report.line',
            'view_id': self.env.ref('ccv_bao_cao.tree_rp_thu_tien_report_line').id,
            'domain': [('id', 'in', self.line_ids.ids)],
        }

    def action_print_pdf_report(self):
        self.ensure_one()
        return self.env.ref('ccv_bao_cao.report_rp_thu_tien_report_pdf').report_action(self)
