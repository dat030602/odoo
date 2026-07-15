from odoo import models, fields, api

class SalarySalesCommission(models.Model):
    """Bảng tính Hoa hồng từng khu vực"""
    _name = 'salary.sales.commission'
    _description = 'Salary Sales Commission'
    _order = 'team_id'

    name = fields.Char(string='Tên', related='team_id.report_name')
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', required=True)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    
    # Liên kết tới dòng tổng hợp theo khu vực
    total_line_id = fields.Many2one(
        'salary.sales.summary.total.line',
        string='Dòng tổng hợp khu vực',
        ondelete='set null'
    )

    # Dữ liệu từ bảng tổng hợp doanh thu (liên kết trực tiếp từ total_line)
    total_revenue = fields.Monetary(string='Doanh thu', compute='_compute_commission_values', store=True, readonly=True)
    total_payment_received = fields.Monetary(string='Thu tiền', compute='_compute_commission_values', store=True, readonly=True)
    achievement_rate = fields.Float(string='Tỷ lệ hoàn thành', compute='_compute_commission_values', store=True, readonly=True)
    
    # Tính toán hoa hồng
    revenue_ratio = fields.Float(string='Tỷ lệ thanh toán', compute='_compute_commission_values', store=True, readonly=True)
    commission_amount = fields.Monetary(string='Thưởng', compute='_compute_commission_values', store=True)
    status = fields.Selection([
        ('achieved', 'Đạt'),
        ('not_achieved', 'Không đạt')
    ], string='Trạng thái', compute='_compute_commission_values', store=True)
    
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('total_line_id.total_revenue', 'total_line_id.total_payment_received', 'total_line_id.achievement_rate')
    def _compute_commission_values(self):
        for record in self:
            record.total_revenue = record.total_line_id.total_revenue
            record.total_payment_received = record.total_line_id.total_payment_received
            record.achievement_rate = record.total_line_id.achievement_rate
            record.revenue_ratio = record.total_line_id.payment_rate
            if record.total_line_id:
                # Tính thưởng theo quy tắc dựa trên achievement_rate (0..1)
                achievement_rate = record.achievement_rate or 0.0
                if achievement_rate >= 1:
                    total_payment_received = record.total_payment_received
                else:
                    total_payment_received = record.total_payment_received * achievement_rate

                if achievement_rate >= 0.90:
                    record.commission_amount = total_payment_received * 0.2 / 100  # 0.2%
                elif achievement_rate >= 0.75:
                    record.commission_amount = total_payment_received * 0.06 / 100  # 0.06%
                else:
                    record.commission_amount = 0.0
                record.status = 'achieved' if achievement_rate >= 0.90 else 'not_achieved'
            else:
                record.commission_amount = 0.0
                record.status = 'not_achieved'

    def action_view_summary_lines(self):
        """Action để xem chi tiết các dòng tổng hợp của khu vực"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Chi tiết khu vực {self.team_id.name}',
            'res_model': 'salary.sales.summary.line',
            'view_mode': 'tree,form',
            'domain': [('summary_id', '=', self.summary_id.id), ('team_id', '=', self.team_id.id)],
            'context': {
                'default_summary_id': self.summary_id.id,
                'default_team_id': self.team_id.id,
            },
            'target': 'current',
        }
