# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TrpApproveConfigLineDetail(models.Model):
    _name = 'trp.approve.config.line'
    _description = 'Quy tắc duyệt'
    _order = "type, level"

    trp_approve_config_id = fields.Many2one('trp.approve.config', string="Cấu hình duyệt", ondelete="cascade")
    name = fields.Char(string="Name")
    type = fields.Selection([('new', 'Mới'), ('cancel', 'Hủy')], string="Phân loại")
    condition = fields.Text(string="Điều kiện", help="[('state', '=',  'draft')]")
    level = fields.Integer(string="Cấp duyệt")
    priority = fields.Integer(string="Trình tự")
    manager_type = fields.Selection([('parent', 'Quản lý trực tiếp'), ('manager', 'Trưởng phòng'), ('delegate', 'Ký nháy')], string='Loại quản lý', default='manager')
    user_ids = fields.Many2many('res.users', string="Người duyệt")
    job_ids = fields.Many2many('hr.job', string="Chức vụ duyệt")
    do_agree = fields.Char(string="Cập nhật đồng ý", help="Khai báo kiểu Dictionary")
    do_refuse = fields.Char(string="Cập nhật từ chối", help="Khai báo kiểu Dictionary")
    is_applied = fields.Boolean(string="Đã áp dụng", default=False)
    title = fields.Char(string="Tiêu đề")
    allow_sign = fields.Integer(string="Ký nháy", default=0)
    approval_mode = fields.Selection([
        ('any', 'Bất kỳ ai duyệt'),
        ('all', 'Tất cả đều phải duyệt')
    ], string='Chế độ duyệt', default='any', help="Bất kỳ ai duyệt: chỉ cần 1 người duyệt. Tất cả đều phải duyệt: cần tất cả người duyệt")
    delegate_approver_ids = fields.Many2many('res.users', 'delegate_approve_config_line_users_rel', string="Người duyệt được ủy quyền")
