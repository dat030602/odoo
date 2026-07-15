from odoo import models, fields, api

class SalaryBonusCommission(models.Model):
    """Hoa hồng thưởng thêm theo doanh số"""
    _name = 'salary.bonus.commission'
    _description = 'Salary Bonus Commission'
    _order = 'team_id'

    name = fields.Char(string='Tên', related='team_id.report_name')
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', required=True)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    
    # Dữ liệu từ summary lines
    achievement_rate = fields.Float(
        string='Tỷ lệ (%)', 
        compute='_compute_bonus_data', 
        store=True,
        help='Lấy từ cột "Tỷ lệ" ở mục 1'
    )
    
    # Tính toán thưởng thêm
    bonus_amount = fields.Monetary(
        string='Số tiền đạt được', 
        compute='_compute_bonus_data', 
        store=True,
        help='Count số dòng * 1.000.000đ'
    )
    
    # Điều kiện đạt thưởng
    is_qualified = fields.Boolean(
        string='Đạt điều kiện', 
        compute='_compute_bonus_data', 
        store=True,
        help='Kv=90% sản lượng, TS đạt 90%, TKV nhận 1tr'
    )
    
    # Chi tiết số dòng đạt điều kiện
    qualified_lines_count = fields.Integer(
        string='Số nhân viên đạt điều kiện', 
        compute='_compute_bonus_data', 
        store=True
    )
    
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('summary_id.month', 'summary_id.year', 'summary_id.total_line_ids.achievement_rate', 'team_id')
    def _compute_bonus_data(self):
        for record in self:
            if not record._is_bonus_applicable_period():
                record.achievement_rate = 0.0
                record.qualified_lines_count = 0
                record.is_qualified = False
                record.bonus_amount = 0.0
                continue

            # Lấy dòng tổng hợp theo khu vực (total lines) của team này
            team_lines = record.summary_id.total_line_ids.filtered(lambda line: line.team_id == record.team_id)
            
            if team_lines:
                # Tính tỷ lệ trung bình của team
                achievement_rates = team_lines.mapped('achievement_rate')
                record.achievement_rate = sum(achievement_rates) / len(achievement_rates) if achievement_rates else 0.0
            else:
                record.achievement_rate = 0.0

            date_from, date_to = record.summary_id._get_date_range()
            team_id = record.team_id
            
            # Lấy danh sách nhân viên bị loại trừ từ config
            excluded_employee_ids = self.env['res.config.settings'].get_excluded_employee_ids()
            
            # Tạo domain để loại trừ nhân viên
            domain = [
                ('period_id.date_start', '>=', date_from.strftime('%Y-%m-%d %H:%M:%S')),
                ('period_id.date_end', '<=', date_to.strftime('%Y-%m-%d %H:%M:%S')),
                ('employee_id.user_id.sale_team_id', '=', team_id.id),
                ('employee_id.user_id', '!=', team_id.user_id.id)
            ]
            
            # Thêm điều kiện loại trừ nhân viên nếu có
            if excluded_employee_ids:
                domain.append(('employee_id', 'not in', excluded_employee_ids))
            
            team_lines = self.env['kpi.scorecard.line'].with_context(lang='vi_VN').search(domain).filtered(lambda line:'doanh số' in line.kpi_id.name.lower())

            qualified_lines_count = 0
            qualified_lines_count = len(team_lines.filtered(lambda line: (line.actual_value / (line.target_value or 1)) >= 0.9))

            record.qualified_lines_count = qualified_lines_count
            record.is_qualified = record.achievement_rate >= 0.9 and record.qualified_lines_count > 0
            record.bonus_amount = (record.qualified_lines_count * 1000000) if record.is_qualified else 0

    def _is_bonus_applicable_period(self):
        self.ensure_one()
        try:
            month_int = int(self.summary_id.month)
            year_int = int(self.summary_id.year)
        except Exception:
            return False
        return year_int > 2026 or (year_int == 2026 and month_int >= 3)

    def action_recompute(self):
        self._compute_bonus_data()

    def action_view_team_summary_lines(self):
        """Action để xem tất cả summary lines của team"""
        self.ensure_one()
        
        team_lines = self.summary_id.line_ids.filtered(lambda line: line.team_id == self.team_id)
        
        if team_lines:
            return {
                'type': 'ir.actions.act_window',
                'name': f'Tất cả dòng tổng hợp - {self.team_id.name}',
                'res_model': 'salary.sales.summary.line',
                'res_ids': team_lines.ids,
                'view_mode': 'tree,form',
                'domain': [('id', 'in', team_lines.ids)],
                'context': {
                    'default_summary_id': self.summary_id.id,
                    'default_team_id': self.team_id.id,
                },
                'target': 'current',
            }
        return False
