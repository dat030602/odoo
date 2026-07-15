# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class CcvChiTietCongNoPhaiThu(models.Model):
    _name = 'ccv.chi.tiet.cong.no.phai.thu'
    _description = 'Phiếu Chi Tiết Công Nợ Phải Thu'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string="Tên", default="Chi Tiết Công Nợ Phải Thu", tracking=True)
    date_from = fields.Date(string="Từ ngày", default=lambda s: date.today().replace(day=1), required=True)
    date_to = fields.Date(string="Đến ngày", default=lambda s: date.today(), required=True)
    account_id = fields.Many2one("account.account", string="Tài khoản")

    report_type = fields.Selection([
        ('1', 'Một khách hàng'),
        ('is_many_partner', 'Nhiều khách hàng (tự chọn)'),
        ('team', 'Theo khu vực'),
        ('is_all_partner', 'Tất cả khách hàng'),
    ], default='1', string="Loại báo cáo")
    partner_state = fields.Selection([
        ('0', 'Ẩn'), ('1', 'Một'), ('2', 'Nhiều'),
    ], compute='_compute_partner_state')
    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    partner_ids = fields.Many2many("res.partner", string="Khách hàng")
    team_id = fields.Many2many("crm.team", string="Đội bán hàng")
    page_break = fields.Boolean(string="Xuống dòng khi in", default=False)

    voter_id = fields.Many2one("res.users", string="Người lập phiếu", default=lambda s: s.env.user)
    chief_dept_id = fields.Many2one("res.users", string="Trưởng bộ phận")
    debt_accountant_id = fields.Many2one("res.users", string="Kế toán tổng hợp")
    chief_acc_id = fields.Many2one("res.users", string="Kế toán trưởng")
    unit_heads_id = fields.Many2one("res.users", string="Thủ trưởng đơn vị")

    line_ids = fields.One2many('ccv.chi.tiet.cong.no.phai.thu.line', 'parent_id', string="Chi tiết")
    line_tax_ids = fields.One2many('ccv.chi.tiet.cong.no.phai.thu.line', 'parent_id',
                                   string="Chi tiết bỏ thuế",
                                   compute='_compute_line_tax_ids', store=False)

    total_end_debit = fields.Float(string="Tổng SD nợ cuối kỳ", digits=(16, 0),
                                   compute='_compute_total_end_balance')
    total_end_credit = fields.Float(string="Tổng SD có cuối kỳ", digits=(16, 0),
                                    compute='_compute_total_end_balance')

    @api.depends('line_ids', 'line_ids.end_debit', 'line_ids.end_credit', 'line_ids.partner_id')
    def _compute_total_end_balance(self):
        for rec in self:
            total_debit = 0.0
            total_credit = 0.0
            for partner in rec.line_ids.mapped('partner_id'):
                partner_lines = rec.line_ids.filtered(lambda l: l.partner_id.id == partner.id)
                if partner_lines:
                    total_debit += partner_lines[-1].end_debit
                    total_credit += partner_lines[-1].end_credit
            rec.total_end_debit = total_debit
            rec.total_end_credit = total_credit

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'),
         ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        string='Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many(
        'trp.approve.history', 'ccv_chi_tiet_cong_no_phai_thu_id',
        string='Lịch sử duyệt', copy=False)

    is_user_current = fields.Boolean(compute='_compute_is_user_current')

    @api.depends('current_approve_user_ids')
    def _compute_is_user_current(self):
        for rec in self:
            rec.is_user_current = self.env.user in rec.current_approve_user_ids

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', 'trp_approve_config_line_id.job_ids',
                 'team_id', 'team_id.user_id')
    def _compute_current_approve_users(self):
        super()._compute_current_approve_users()
        for record in self:
            cfg = record.trp_approve_config_line_id
            if cfg and cfg.manager_type == 'team':
                team_leader = record.team_id.mapped('user_id')
                approver_ids = team_leader.ids if team_leader else []
                # Cộng thêm user_ids/job_ids/delegate nếu có cấu hình kèm
                if cfg.user_ids:
                    approver_ids += cfg.user_ids.ids
                for job in cfg.job_ids:
                    approver_ids += job.employee_ids.mapped('user_id').ids
                if record.delegate_approver_ids:
                    approver_ids += record.delegate_approver_ids.ids
                record.current_approve_user_ids = [(6, 0, list(set(approver_ids)))]

    @api.depends('line_ids')
    def _compute_line_tax_ids(self):
        for rec in self:
            rec.line_tax_ids = rec.line_ids.filtered(lambda l: l.display_type != 'tax')

    @api.depends('report_type')
    def _compute_partner_state(self):
        for rec in self:
            if rec.report_type == 'is_many_partner':
                rec.partner_state = '2'
            elif rec.report_type in ('team', 'is_all_partner'):
                rec.partner_state = '0'
            else:
                rec.partner_state = '1'

    @api.onchange('team_id', 'report_type')
    def _onchange_name(self):
        for rec in self:
            if rec.report_type == 'team' and rec.team_id:
                team_names = ', '.join(rec.team_id.mapped('name'))
                rec.name = f"Chi Tiết Công Nợ Phải Thu - {team_names}"
            else:
                rec.name = "Chi Tiết Công Nợ Phải Thu"

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        account = self.env['account.account'].search([('code', '=', '13111')], limit=1)
        defaults.update({
            'voter_id': self.env.user.id,
            'chief_dept_id': int(env_params.get_param('ccv_sql.chief_business_department_id', self.env.user.id)),
            'chief_acc_id': int(env_params.get_param('ccv_sql.chief_accountant_id', self.env.user.id)),
            'unit_heads_id': int(env_params.get_param('ccv_sql.unit_head_id', self.env.user.id)),
            'debt_accountant_id': int(env_params.get_param('ccv_sql.debt_accountant_id', self.env.user.id)),
            'account_id': account.id if account else False,
        })
        return defaults

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise ValidationError(_("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày'."))

    def unlink(self):
        for record in self:
            if record.state not in ('draft', 'refuse', 'cancel') and not self.env.user.has_group('base.group_system'):
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
    # Hành động lấy dữ liệu — uỷ thác cho alpha.report (transient)
    # ------------------------------------------------------------
    def _build_alpha_proxy(self, with_lines=False):
        """Tạo một bản ghi alpha.report tạm dùng filter & người ký giống bản ghi này."""
        AlphaReport = self.env['alpha.report'].sudo()
        proxy = AlphaReport.create({
            'type': 'chi_tiet_cong_no_phai_thu',
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'partner_ids': [(6, 0, self.partner_ids.ids)],
            'report_type': self.report_type,
            'team_id': [(6, 0, self.team_id.ids)],
            'voter_id': self.voter_id.id,
            'chief_dept_id': self.chief_dept_id.id,
            'debt_accountant_id': self.debt_accountant_id.id,
            'chief_acc_id': self.chief_acc_id.id,
            'unit_heads_id': self.unit_heads_id.id,
            'state': self.state,
            'page_break': self.page_break,
        })
        if with_lines:
            Line3 = self.env['alpha.report.line3'].sudo()
            for line in self.line_ids:
                Line3.create(self._copy_line_to_alpha_vals(line, proxy.id))
        return proxy

    def _copy_line_to_alpha_vals(self, line, parent_id):
        return {
            'parent_id': parent_id,
            'date': line.date,
            'partner_id': line.partner_id.id,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'default_code': line.default_code,
            'uom_id': line.uom_id.id,
            'price_unit': line.price_unit,
            'amount_tax': line.amount_tax,
            'account_id': line.account_id.id,
            'account_dest_id': line.account_dest_id.id,
            'debit': line.debit,
            'credit': line.credit,
            'end_debit': line.end_debit,
            'end_credit': line.end_credit,
            'end_w_tax_debit': line.end_w_tax_debit,
            'end_w_tax_credit': line.end_w_tax_credit,
            'move_id': line.move_id.id,
            'reference': line.reference,
            'note': line.note,
            'order_id': line.order_id.id,
            'partner_code': line.partner_code,
            'display_type': line.display_type,
            'level': line.level,
            'move_type': line.move_type,
        }

    def _copy_alpha_to_line_vals(self, line, sequence=10):
        return {
            'parent_id': self.id,
            'sequence': sequence,
            'team_id': line.partner_id.team_id.id if line.partner_id and line.partner_id.team_id else False,
            'date': line.date,
            'partner_id': line.partner_id.id,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'default_code': line.default_code,
            'uom_id': line.uom_id.id,
            'price_unit': line.price_unit,
            'amount_tax': line.amount_tax,
            'account_id': line.account_id.id,
            'account_dest_id': line.account_dest_id.id,
            'debit': line.debit,
            'credit': line.credit,
            'end_debit': line.end_debit,
            'end_credit': line.end_credit,
            'end_w_tax_debit': line.end_w_tax_debit,
            'end_w_tax_credit': line.end_w_tax_credit,
            'move_id': line.move_id.id,
            'reference': line.reference,
            'note': line.note,
            'order_id': line.order_id.id,
            'partner_code': line.partner_code,
            'display_type': line.display_type,
            'level': line.level,
            'move_type': line.move_type,
        }

    def action_confirm(self):
        """Lấy dữ liệu từ Postgres function thông qua alpha.report transient và sao chép sang line_ids."""
        self.ensure_one()
        if self.state not in ('draft',):
            raise UserError(_("Chỉ có thể lấy dữ liệu khi phiếu ở trạng thái Nháp."))
        self.line_ids.unlink()
        proxy = self._build_alpha_proxy(with_lines=False)
        proxy.report_chi_tiet_cong_no_phai_thu()
        # Xây dựng bản đồ thứ tự team
        team_order = {team.id: (idx + 1) * 10 for idx, team in enumerate(self.team_id)}
        Line = self.env['ccv.chi.tiet.cong.no.phai.thu.line'].sudo()
        for ln in proxy.line3_ids:
            partner_team = ln.partner_id.team_id if ln.partner_id else False
            seq = team_order.get(partner_team.id, 9999) if partner_team else 9999
            Line.create(self._copy_alpha_to_line_vals(ln, sequence=seq))
        # transient: sẽ tự dọn dẹp; vẫn unlink để giải phóng ngay
        proxy.sudo().unlink()

    def action_view_tree(self):
        self.ensure_one()
        return {
            'name': "Chi tiết công nợ phải thu",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'ccv.chi.tiet.cong.no.phai.thu.line',
            'view_id': self.env.ref('ccv_sql.tree_ccv_chi_tiet_cong_no_phai_thu_line').id,
            'domain': [('id', 'in', self.line_ids.ids)],
        }

    def _render_via_proxy(self, report_xml_id):
        proxy = self._build_alpha_proxy(with_lines=True)
        try:
            return self.env.ref(report_xml_id).report_action(proxy)
        finally:
            # giữ lại proxy tạm thời để render hoàn tất; transient sẽ tự dọn.
            pass

    def action_print_pdf_report(self):
        return self._render_via_proxy('ccv_sql.chi_tiet_cong_no_phai_thu_report')

    def action_print_report_tax(self):
        return self._render_via_proxy('ccv_sql.chi_tiet_cong_no_phai_thu_tax_report')

    def action_print_xlsx_report(self):
        return self.env.ref('ccv_sql.chi_tiet_cong_no_phai_thu_xlsx').report_action(self)
