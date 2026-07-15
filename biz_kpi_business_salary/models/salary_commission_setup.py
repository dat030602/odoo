from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SalaryCommissionSetup(models.Model):
    """Bảng set up % nhận hoa hồng cho từng khu vực"""
    _name = 'salary.commission.setup'
    _description = 'Salary Commission Setup'
    _order = 'team_id'

    name = fields.Char(string='Tên', related='team_id.report_name')
    team_id = fields.Many2one('crm.team', string='Khu vực', required=True)
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    # Tỷ lệ phần trăm nhận hoa hồng
    sale_support_percent = fields.Float(
        string='Sale hỗ trợ (%)', 
        default=0.0,
        help='Tỷ lệ phần trăm hoa hồng cho Sale hỗ trợ'
    )
    team_leader_percent = fields.Float(
        string='Trưởng khu vực (%)', 
        default=0.0,
        help='Tỷ lệ phần trăm hoa hồng cho Trưởng khu vực'
    )
    department_manager_percent = fields.Float(
        string='Trưởng (Phó) phòng (%)', 
        default=0.0,
        help='Tỷ lệ phần trăm hoa hồng cho Trưởng (Phó) phòng'
    )
    
    # Computed fields để hiển thị tỷ lệ còn lại
    remaining_percent = fields.Float(
        string='Còn lại (%)', 
        compute='_compute_remaining_percent', 
        store=True,
        help='Tỷ lệ phần trăm còn lại sau khi phân chia'
    )
    
    # Các field mới cho phân bổ hoa hồng
    # Tỉ lệ BLĐ/TL: 5%
    leadership_percent = fields.Float(
        string='Tỉ lệ BLĐ/TL (%)',
        default=0.5,
        help='Tỷ lệ phần trăm hoa hồng cho Ban lãnh đạo'
    )
    
    # Các Phòng Ban/TL: 5%
    department_percent = fields.Float(
        string='Các Phòng Ban/TL (%)',
        default=0.5,
        help='Tỷ lệ phần trăm hoa hồng cho các phòng ban'
    )
    
    # Khu vực Phụ trách/TL: 55%
    area_responsible_percent = fields.Float(
        string='Khu vực Phụ trách/TL (%)',
        default=0.55,
        help='Tỷ lệ phần trăm hoa hồng cho khu vực phụ trách'
    )
    
    # Trưởng phòng: 20%
    department_head_percent = fields.Float(
        string='Trưởng phòng (%)',
        default=0.2,
        help='Tỷ lệ phần trăm hoa hồng cho trưởng phòng'
    )
    
    # Điều tiết: 5%
    regulation_percent = fields.Float(
        string='Điều tiết (%)',
        default=0.05,
        help='Tỷ lệ phần trăm hoa hồng cho điều tiết'
    )
    
    structured_personnel_percent = fields.Float(
        string='Nhân sự được cơ cấu (%)',
        default=0.1,
        help='Tỷ lệ phần trăm hoa hồng cho nhân sự được cơ cấu'
    )

    @api.depends('sale_support_percent', 'team_leader_percent', 'department_manager_percent')
    def _compute_remaining_percent(self):
        for record in self:
            total_allocated = record.sale_support_percent + record.team_leader_percent + record.department_manager_percent
            record.remaining_percent = 1 - total_allocated

    @api.constrains('sale_support_percent', 'team_leader_percent', 'department_manager_percent')
    def _check_percent_total(self):
        for record in self:
            total = record.sale_support_percent + record.team_leader_percent + record.department_manager_percent
            if total > 100.0:
                raise ValidationError('Tổng tỷ lệ phần trăm không được vượt quá 100%')
            if any(percent < 0 for percent in [record.sale_support_percent, record.team_leader_percent, record.department_manager_percent]):
                raise ValidationError('Tỷ lệ phần trăm không được âm')
