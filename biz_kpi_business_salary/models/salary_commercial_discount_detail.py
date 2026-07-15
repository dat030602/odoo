from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SalaryCommercialDiscountDetail(models.Model):
    """Chi tiết chiết khấu thương mại"""
    _name = 'salary.commercial.discount.detail'
    _description = 'Salary Commercial Discount Detail'
    _order = 'summary_id, team_id'

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', related='summary_id.team_id')
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    
    # Liên kết với setup tỷ lệ hoa hồng
    commission_setup_id = fields.Many2one(
        'salary.commission.setup',
        string='Setup tỷ lệ hoa hồng',
        compute='_compute_commission_setup',
        store=True,
        help='Setup tỷ lệ hoa hồng tương ứng với khu vực'
    )

    total_quantity = fields.Float(
        string='Sản lượng',
        compute='_compute_commission_amounts',
        store=True,
        help='Tổng sản lượng'
    )
    total_revenue = fields.Monetary(
        string='Doanh thu',
        compute='_compute_commission_amounts',
        store=True,
        help='Tổng doanh thu'
    )
    total_payment = fields.Monetary(
        string='Tiền thanh toán',
        compute='_compute_commission_amounts',
        store=True,
        help='Tổng tiền thanh toán'
    )
    
    # Tổng tiền hoa hồng (100%)
    total_commission_amount = fields.Monetary(
        string='Tiền hoa hồng',
        compute='_compute_commission_amounts',
        store=True,
        help='Tổng tiền hoa hồng (100%)'
    )
    
    # Phân bổ hoa hồng theo tỷ lệ
    leadership_amount = fields.Monetary(
        string='BLĐ',
        compute='_compute_commission_amounts',
        store=True,
        help='Số tiền hoa hồng cho Ban lãnh đạo'
    )
    
    department_amount = fields.Monetary(
        string='Các Phòng Ban',
        compute='_compute_commission_amounts',
        store=True,
        help='Số tiền hoa hồng cho các phòng ban'
    )
    
    area_responsible_amount = fields.Monetary(
        string='Khu vực Phụ trách',
        compute='_compute_commission_amounts',
        store=True,
        help='Số tiền hoa hồng cho khu vực phụ trách'
    )
    
    department_head_amount = fields.Monetary(
        string='Trưởng phòng',
        compute='_compute_commission_amounts',
        store=True,
        help='Số tiền hoa hồng cho trưởng phòng'
    )
    
    regulation_amount = fields.Monetary(
        string='Điều tiết',
        compute='_compute_commission_amounts',
        store=True,
        help='Số tiền hoa hồng cho điều tiết'
    )
    
    structured_personnel_amount = fields.Monetary(
        string='Nhân sự được cơ cấu',
        compute='_compute_commission_amounts',
        store=True,
        help='Số tiền hoa hồng cho nhân sự được cơ cấu'
    )
    
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('team_id', 'summary_id.team_id')
    def _compute_commission_setup(self):
        """Lấy setup tỷ lệ hoa hồng dựa trên team_id"""
        for record in self:
            if not record.team_id:
                record.commission_setup_id = False
                continue
            
            team_id = record.summary_id.team_id or record.team_id
            
            setup = self.env['salary.commission.setup'].search([('team_id', '=', team_id.id), ('leadership_percent', '>', 0)], limit=1)
            
            record.commission_setup_id = setup.id if setup else False

    @api.depends('summary_id.total_line_ids.total_revenue', 'commission_setup_id')
    def _compute_commission_amounts(self):
        """Tính toán các khoản hoa hồng dựa trên tỷ lệ từ setup"""
        for record in self:
            record.total_commission_amount = 0
            record.total_payment = 0
            record.total_revenue = 0
            record.total_quantity = 0
            if record.team_id:
                for line in record.summary_id.total_line_ids.filtered(lambda x: x.team_id == record.team_id):
                    record.total_payment += line.total_payment_received
                    record.total_revenue += line.total_revenue
                    record.total_quantity += line.production_quantity
            record.total_commission_amount = record.total_quantity * (record.summary_id.price_unit_commercial or 0) * record.total_revenue / (record.total_payment or record.total_revenue or 1)
            
            setup = record.commission_setup_id
            
            # Tính toán theo tỷ lệ (tỷ lệ đã là dạng thập phân, ví dụ 0.05 = 5%)
            record.leadership_amount = record.total_commission_amount * (setup.leadership_percent or 0)
            record.department_amount = record.total_commission_amount * (setup.department_percent or 0)
            record.area_responsible_amount = record.total_commission_amount * (setup.area_responsible_percent or 0)
            record.department_head_amount = record.total_commission_amount * (setup.department_head_percent or 0)
            record.regulation_amount = record.total_commission_amount * (setup.regulation_percent or 0)
            record.structured_personnel_amount = record.total_commission_amount * (setup.structured_personnel_percent or 0)

    @api.depends('team_id.name', 'summary_id.name')
    def _compute_name(self):
        """Tạo tên cho record"""
        for record in self:
            team_name = record.team_id.name if record.team_id else ''
            summary_name = record.summary_id.name if record.summary_id else ''
            record.name = f'{summary_name} - {team_name}'
