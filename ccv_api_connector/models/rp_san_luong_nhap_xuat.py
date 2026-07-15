# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date

import logging

_logger = logging.getLogger(__name__)


class RpSanLuongNhapXuatLine(models.Model):
    _name = 'rp.san.luong.nhap.xuat.line'
    _description = 'Chi tiết sản lượng nhập xuất'
    _order = 'id'

    parent_id = fields.Many2one('rp.san.luong.nhap.xuat', string='Báo cáo', ondelete='cascade')
    no = fields.Integer(string='STT')
    date = fields.Date(string='Ngày')
    type = fields.Char(string='Loại')
    partner_name = fields.Char(string='Đại lý/NCC')
    order = fields.Char(string='Đơn hàng')
    vehicle_num = fields.Char(string='Số xe')
    vehicle_driver = fields.Char(string='Tài xế')
    uom_name = fields.Char(string='ĐVT')
    quantity = fields.Float(string='Số lượng phiếu kho', digits=(16, 3))
    gate = fields.Char(string='Cửa nhập/xuất')
    loading = fields.Char(string='Bốc xếp')
    stocker = fields.Char(string='Thủ kho')
    note = fields.Char(string='Ghi chú')
    weighing_tl_hang = fields.Float(string='TL hàng', digits=(16, 3))
    weighing_tl_bao_bi = fields.Float(string='TL bao bì', digits=(16, 3))
    weighing_tl_sau_tru_bao_bi = fields.Float(string='TL sau trừ bao bì', digits=(16, 3))


class RpSanLuongNhapXuat(models.Model):
    _name = 'rp.san.luong.nhap.xuat'
    _description = 'Báo cáo sản lượng nhập xuất'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _order = 'id desc'

    name = fields.Char(string='Tên', compute='_compute_name', store=True, readonly=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approve', 'Đang duyệt'),
        ('approved', 'Đã duyệt'),
        ('refuse', 'Từ chối'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='draft', tracking=True)

    # Bộ lọc
    date = fields.Date(string='Từ ngày', default=lambda s: date.today(), required=True)
    date_to = fields.Date(string='Đến ngày', default=lambda s: date.today(), required=True)
    department_id = fields.Many2one('hr.department', string='Phòng ban')
    type = fields.Selection([('in', 'Nhập'), ('out', 'Xuất')], string='Loại')
    is_next_day_fall_vehicle = fields.Boolean(string='Xe rớt', help='Khi tích vào, báo cáo sẽ in theo xe rớt')

    # Người ký tên
    voter_id = fields.Many2one('res.users', string='Người Lập Biểu',
                               default=lambda self: self.env.user)
    loading_id = fields.Many2one('res.users', string='Bộ nhận bốc xếp')
    stocker_id = fields.Many2one('res.users', string='Chuyên viên kiểm soát kho')
    hr_admin_department_id = fields.Many2one('res.users', string='Phòng HCNS')
    chief_finance_id = fields.Many2one('res.users', string='Phòng Kế toán')
    director_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')

    # Chi tiết
    line_ids = fields.One2many('rp.san.luong.nhap.xuat.line', 'parent_id', string='Chi tiết', copy=False)

    # Lịch sử duyệt
    trp_approve_history_ids = fields.One2many(
        'trp.approve.history', 'rp_san_luong_nhap_xuat_id',
        string='Lịch sử duyệt', copy=False)

    is_user_current = fields.Boolean(compute='_compute_is_user_current')

    @api.depends('current_approve_user_ids')
    def _compute_is_user_current(self):
        for rec in self:
            rec.is_user_current = self.env.user in rec.current_approve_user_ids

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        defaults.update({
            'voter_id': self.env.user.id,
            'chief_finance_id': int(env_params.get_param('ccv_bao_cao.chief_accountant_id', 0)) or False,
            'hr_admin_department_id': int(env_params.get_param('ccv_bao_cao.hr_admin_department_id', 0)) or False,
            'stocker_id': int(env_params.get_param('ccv_bao_cao.stocker_id', 0)) or False,
            'director_id': int(env_params.get_param('ccv_bao_cao.director_id', 0)) or False,
        })
        return defaults

    @api.constrains('date', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_to and rec.date and rec.date_to < rec.date:
                raise ValidationError(_("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày'."))

    @api.onchange('department_id')
    def _onchange_department_ids(self):
        for rec in self:
            if rec.department_id:
                emp = self.env['hr.employee'].search(
                    [('department_id', '=', rec.department_id.id)], limit=1)
                rec.loading_id = emp.parent_id.user_id if emp and emp.parent_id else False

    def unlink(self):
        for record in self:
            # Allow admin to delete reports in any state
            if not self.env.user.has_group('base.group_system') and record.state not in ('draft', 'refuse', 'cancel'):
                raise UserError(_("Không thể xóa báo cáo đã/đang duyệt!"))
        return super().unlink()

    # ────────────────────────────────────────────────────────────
    # Compute name
    # ────────────────────────────────────────────────────────────
    @api.depends('date', 'date_to', 'department_id', 'type')
    def _compute_name(self):
        for rec in self:
            parts = ['Báo cáo sản lượng nhập xuất']
            if rec.date and rec.date_to and rec.date != rec.date_to:
                parts.append(f"từ {rec.date.strftime('%d/%m/%Y')} đến {rec.date_to.strftime('%d/%m/%Y')}")
            elif rec.date:
                parts.append(f"ngày {rec.date.strftime('%d/%m/%Y')}")
            if rec.department_id:
                parts.append(f"- {rec.department_id.name}")
            if rec.type:
                parts.append(f"({'Nhập' if rec.type == 'in' else 'Xuất'})")
            rec.name = ' '.join(parts)

    # ────────────────────────────────────────────────────────────
    # Lấy dữ liệu
    # ────────────────────────────────────────────────────────────
    def action_confirm(self):
        self.ensure_one()
        if self.state not in ('draft',):
            raise UserError(_("Chỉ có thể lấy dữ liệu khi báo cáo ở trạng thái Nháp."))
        self.line_ids.unlink()

        if self.is_next_day_fall_vehicle:
            domain = [('is_next_day', '=', True)]
        else:
            domain = [('sale_vehicle_id', '!=', False)]

        if self.date:
            domain.append(('sale_vehicle_id.date', '>=', self.date))
        if self.date_to:
            domain.append(('sale_vehicle_id.date', '<=', self.date_to))
        if self.type:
            domain.append(('type', '=', self.type))

        line_ids = self.env['sale.vehicle.in.out.line'].search(domain).sorted(
            lambda line: (1 if (line.note and 'Xe rớt' in line.note) else 0, line.loading_id.name or ""))

        filter_department_id = False
             
        if self.department_id:
            filter_department_line_ids = line_ids.filtered(lambda line: line.loading_id == self.department_id or line.loading2_id == self.department_id)
            filter_department_id = True        

        Line = self.env['rp.san.luong.nhap.xuat.line'].sudo()
        count = 0
        for line_id in line_ids:
            department_id_match_loading1= False
            department_id_match_loading2 = False

            if self.department_id:           
                department_id_match_loading1 = line_id.loading_id == self.department_id
                department_id_match_loading2 = line_id.loading2_id == self.department_id           

            count += 1
            order = (line_id.sale_order_ids.mapped('name')
                     if line_id.sale_order_ids and line_id.type == 'out'
                     else line_id.purchase_order_ids.mapped('name'))
            # Debug: Check data values
            gate_value = str(line_id.gate) if line_id.gate else ''
            loading_value = (line_id.loading_id.name if line_id.loading_id
                            else (line_id.loading or ''))

            # Determine if both loading teams are present reliably
            has_loading1 = bool((line_id.loading and str(line_id.loading) != 'False') or line_id.loading_id)
            has_loading2 = bool((line_id.loading2 and str(line_id.loading2) != 'False') or line_id.loading2_id)
            divide_qty = has_loading1 and has_loading2
            stocker_value = (line_id.stocker_id.name_without_position if line_id.stocker_id
                            else (line_id.stocker or ''))
            note_value = (line_id.user_note if self.is_next_day_fall_vehicle
                         else (line_id.note or ''))

            # Log debug info for first few records when department_id is empty
            if not self.department_id and count <= 3:
                _logger.info(f"Line {count}: gate={gate_value}, loading={loading_value}, stocker={stocker_value}, note={note_value}")
                _logger.info(f"Raw data: line_id.gate={line_id.gate}, line_id.loading={line_id.loading}, line_id.stocker={line_id.stocker}, line_id.note={line_id.note}")
            
            if not filter_department_id or department_id_match_loading1:
                Line.create({
                    'parent_id': self.id,
                    'no': count,
                    'date': line_id.sale_vehicle_id.date if line_id.sale_vehicle_id else False,
                    'type': 'Xuất' if line_id.type == 'out' else 'Nhập',
                    'partner_name': line_id.partner_name or '',
                    'order': ','.join(order) if order else '',
                    'vehicle_num': line_id.vehicle_num or '',
                    'vehicle_driver': (line_id.vehicle_driver
                                    if line_id.vehicle_driver and line_id.vehicle_driver != 'False'
                                    else ''),
                    'uom_name': line_id.uom_id.name if line_id.uom_id else '',
                    'quantity': line_id.quantity / 2 if divide_qty else line_id.quantity,
                    'gate': gate_value,
                    'loading': loading_value,
                    'stocker': stocker_value,
                    'note': note_value,
                    'weighing_tl_hang': line_id.weighing_tl_hang or 0.0,
                    'weighing_tl_bao_bi': line_id.weighing_tl_bao_bi or 0.0,
                    'weighing_tl_sau_tru_bao_bi': line_id.weighing_tl_sau_tru_bao_bi or 0.0,
                })

            if has_loading2 and (not filter_department_id or department_id_match_loading2):
                loading2_value = (line_id.loading2_id.name if line_id.loading2_id else (line_id.loading2 or ''))
                Line.create({
                    'parent_id': self.id,
                    'no': count,
                    'date': line_id.sale_vehicle_id.date if line_id.sale_vehicle_id else False,
                    'type': 'Xuất' if line_id.type == 'out' else 'Nhập',
                    'partner_name': line_id.partner_name or '',
                    'order': ','.join(order) if order else '',
                    'vehicle_num': line_id.vehicle_num or '',
                    'vehicle_driver': (line_id.vehicle_driver
                                    if line_id.vehicle_driver and line_id.vehicle_driver != 'False'
                                    else ''),
                    'uom_name': line_id.uom_id.name if line_id.uom_id else '',
                    'quantity': line_id.quantity / 2 if divide_qty else line_id.quantity,
                    'gate': gate_value,
                    'loading': loading2_value,
                    'stocker': stocker_value,
                    'note': note_value,
                    'weighing_tl_hang': line_id.weighing_tl_hang or 0.0,
                    'weighing_tl_bao_bi': line_id.weighing_tl_bao_bi or 0.0,
                    'weighing_tl_sau_tru_bao_bi': line_id.weighing_tl_sau_tru_bao_bi or 0.0,
                })

    # ────────────────────────────────────────────────────────────
    # Quy trình duyệt
    # ────────────────────────────────────────────────────────────
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
        self.env['mail.activity'].search(
            [('trp_approve_history_id', 'in', res_history.ids)]
        ).with_context(skip_approve_done=True).action_done()

    def action_undo(self):
        self.write({'state': 'draft'})

    # ────────────────────────────────────────────────────────────
    # In báo cáo PDF
    # ────────────────────────────────────────────────────────────
    def action_generate_report(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Vui lòng lấy dữ liệu trước khi in!"))
        return self.env.ref(
            'ccv_api_connector.rp_san_luong_nhap_xuat_pdf_report'
        ).report_action(self)
