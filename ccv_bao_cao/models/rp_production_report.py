# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class RpProductionReport(models.Model):
    _name = 'rp.production.report'
    _description = 'Phiếu Báo cáo sản lượng'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string="Tên", default="Báo cáo sản lượng", tracking=True,
                       required=True)
    date_from = fields.Date(string="Từ ngày", default=lambda s: date.today(), required=True)
    date_to = fields.Date(string="Đến ngày", default=lambda s: date.today(), required=True)
    picking_type_ids = fields.Many2many(
        'stock.picking.type',
        string='Loại hoạt động',
        domain=[("code", "=", "mrp_operation")],
        help="Chọn các loại hoạt động cụ thể để đưa vào báo cáo. Để trống để lấy tất cả.",
    )

    # Người ký
    voter_id = fields.Many2one('res.users', string='Người Lập Biểu',
                               default=lambda s: s.env.user)
    factory_team_leader_id = fields.Many2one('res.users', string='Tổ Trưởng Nhà Máy')
    finished_goods_warehouse_keeper_id = fields.Many2one('res.users', string='Chuyên viên kiểm soát kho')
    hr_admin_department_id = fields.Many2one('res.users', string='Phòng HCNS')
    chief_finance_id = fields.Many2one('res.users', string='Phòng kế toán')
    director_id = fields.Many2one('res.users', string='Ban Lãnh đạo')

    line_ids = fields.One2many('rp.production.report.line', 'parent_id', string="Chi tiết")

    state = fields.Selection(
        [('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'),
         ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
        string='Trạng thái', default='draft', tracking=True)

    trp_approve_history_ids = fields.One2many(
        'trp.approve.history', 'rp_production_report_id',
        string='Lịch sử duyệt', copy=False)

    is_user_current = fields.Boolean(compute='_compute_is_user_current')

    @api.depends('current_approve_user_ids')
    def _compute_is_user_current(self):
        for rec in self:
            rec.is_user_current = self.env.user in rec.current_approve_user_ids

    @api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
                 'trp_approve_config_line_id.user_ids', 'trp_approve_config_line_id.job_ids',
                 'factory_team_leader_id')
    def _compute_current_approve_users(self):
        super()._compute_current_approve_users()
        for record in self:
            cfg = record.trp_approve_config_line_id
            if cfg and cfg.manager_type == 'factory_team_leader':
                leader = record.factory_team_leader_id
                approver_ids = leader.ids if leader else []
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
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        hr_admin_department_id = env_params.get_param('ccv_bao_cao.hr_admin_department_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        finished_goods_warehouse_keeper_id = env_params.get_param(
            'ccv_bao_cao.finished_goods_warehouse_keeper_id', False)
        defaults.update({
            'voter_id': self.env.user.id,
            'hr_admin_department_id': int(hr_admin_department_id) if hr_admin_department_id else False,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'director_id': int(director_id) if director_id else False,
            'finished_goods_warehouse_keeper_id': int(finished_goods_warehouse_keeper_id) if finished_goods_warehouse_keeper_id else False,
        })
        return defaults

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise ValidationError(_("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày'."))

    @api.onchange('picking_type_ids')
    def _onchange_picking_type_ids(self):
        for rec in self:
            if rec.picking_type_ids:
                rec.factory_team_leader_id = rec.picking_type_ids[-1].user_id
            else:
                rec.factory_team_leader_id = False
            rec._update_name()

    @api.onchange('date_from', 'date_to')
    def _onchange_date_range(self):
        for rec in self:
            rec._update_name()

    def _update_name(self):
        self.ensure_one()
        parts = ["Báo cáo sản lượng"]
        if self.picking_type_ids:
            names = self.picking_type_ids.mapped('display_name')
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
            # Admin có thể xóa bất kỳ trạng thái nào
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
        """Lấy dữ liệu báo cáo sản lượng từ mrp.production."""
        self.ensure_one()
        if self.state not in ('draft',):
            raise UserError(_("Chỉ có thể lấy dữ liệu khi phiếu ở trạng thái Nháp."))
        self.line_ids.unlink()

        start_datetime = fields.Datetime.to_datetime(self.date_from)
        end_datetime = fields.Datetime.end_of(fields.Datetime.to_datetime(self.date_to), 'day')

        picking_type_ids = self.picking_type_ids \
            or self.env['stock.picking.type'].search([("code", "=", "mrp_operation")])

        Line = self.env['rp.production.report.line'].sudo()
        count = 0
        for picking_type_id in picking_type_ids:
            mrps = self.env['mrp.production'].search([
                ('stock_date_receipt', '>=', start_datetime),
                ('stock_date_receipt', '<=', end_datetime),
                ('picking_type_id', '=', picking_type_id.id),
                ('state', '=', 'done'),
            ]).sorted('stock_date_receipt')
            for mrp in mrps:
                count += 1
                Line.create({
                    'parent_id': self.id,
                    'no': count,
                    'stock_date_receipt': mrp.stock_date_receipt,
                    'name': mrp.name,
                    'product_id': mrp.product_id.id,
                    'product_code': mrp.product_id.default_code or '',
                    'product_name': mrp.product_id.name,
                    'uom_id': mrp.product_uom_id.id,
                    'quantity': mrp.qty_produced,
                    'user_id': mrp.user_id.id if mrp.user_id else False,
                    'picking_type_id': picking_type_id.id,
                })

    def action_view_tree(self):
        self.ensure_one()
        return {
            'name': _("Chi tiết Báo cáo sản lượng"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'rp.production.report.line',
            'view_id': self.env.ref('ccv_bao_cao.tree_rp_production_report_line').id,
            'domain': [('id', 'in', self.line_ids.ids)],
        }

    def action_print_pdf_report(self):
        """In báo cáo sản lượng dạng PDF."""
        self.ensure_one()
        return self.env.ref('ccv_bao_cao.report_rp_production_report_pdf').report_action(self)
