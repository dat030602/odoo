from odoo import models, fields, api

class SalaryCommissionResult(models.Model):
    """Kết quả tính toán hoa hồng"""
    _name = 'salary.commission.result'
    _description = 'Salary Commission Result'
    _order = 'summary_id, calc_id, commission_type, employee_id'

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    calc_id = fields.Many2one('salary.commission.calculation', string='Công thức tính toán', ondelete='cascade')
    result_name = fields.Char(string='Khoản mục')
    employee_id = fields.Many2one('hr.employee', string='Nhân viên áp dụng')
    employee_code = fields.Char(string='Mã nhân viên', related='employee_id.code', store=True)
    team_id = fields.Many2one('crm.team', string='Khu vực')
    achievement_rate = fields.Float(string='Tỷ lệ')
    plan_rate = fields.Float(string='Tỷ lệ kế hoạch')
    completion_rate = fields.Float(string='Tỷ lệ hoàn thành')
    calc_name = fields.Char(string='Tên công thức', related='calc_id.name', store=True)
    
    # Kết quả tính toán
    amount = fields.Monetary(string='Số tiền hoa hồng', required=True)
    sales_discount_amount = fields.Monetary(string='Chiết khấu bán hàng')
    humic_discount_amount = fields.Monetary(string='Chiết khấu Humic')
    amount_80 = fields.Monetary(string='Thực nhận 80%')
    amount_20 = fields.Monetary(string='Giữ lại 20%')
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)
    
    # Ghi chú
    note = fields.Text(string='Ghi chú')
    
    # Thông tin bổ sung
    commission_type = fields.Selection(related='calc_id.commission_type', string='Loại hoa hồng', store=True)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active', store=True)

    @api.depends('calc_id.name', 'result_name', 'employee_id.name', 'amount')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.result_name or record.calc_id.name or ''} - {record.employee_id.name or ''} - {record.amount:,.0f}"

    @api.model
    def create_commission_results(self, summary_id, results_data):
        """
        Tạo kết quả tính toán hoa hồng
        
        Args:
            summary_id: ID của salary.sales.summary
            results_data: Dict với format:
                {
                    calc_id: {
                        employee_id: {
                            'amount': float,
                        }
                    }
                }
        """
        if not summary_id or not results_data:
            return False
        
        # Xóa dữ liệu cũ cho summary này
        self.search([('summary_id', '=', summary_id)]).unlink()
        
        # Tạo dữ liệu mới
        vals_list = []
        for calc_id, employees_data in results_data.items():
            # Skip combined results (they start with "combined_")
            if isinstance(calc_id, str) and calc_id.startswith('combined_'):
                continue
                
            for employee_id, data in employees_data.items():
                vals_list.append({
                    'summary_id': summary_id,
                    'calc_id': calc_id,
                    'employee_id': employee_id,
                    'amount': data.get('amount', 0.0),
                    'amount_80': data.get('amount_80', data.get('amount', 0.0) * 0.8),
                    'amount_20': data.get('amount_20', data.get('amount', 0.0) * 0.2),
                })
        
        return self.create(vals_list)

    @api.model
    def create_combined_commission_results(self, summary_id, combined_results):
        """
        Tạo kết quả tổng hợp cho các loại hoa hồng có nhiều calculation
        
        Args:
            summary_id: ID của salary.sales.summary
            combined_results: Dict với format:
                {
                    'combined_monthly': {
                        'amount': float,
                        'individual_calc_ids': [1, 2, 3],
                        'note': str
                    }
                }
        """
        if not summary_id or not combined_results:
            return False
        
        vals_list = []
        for combined_key, data in combined_results.items():
            if not isinstance(combined_key, str) or not combined_key.startswith('combined_'):
                continue
                
            # Get the first calculation to use as reference
            first_calc_id = data.get('individual_calc_ids', [None])[0]
            if not first_calc_id:
                continue
                
            # Create a combined result record
            vals_list.append({
                'summary_id': summary_id,
                'calc_id': first_calc_id,  # Use first calc as reference
                'employee_id': False,  # Combined result, no specific employee
                'amount': data.get('amount', 0.0),
                'amount_80': data.get('amount_80', data.get('amount', 0.0) * 0.8),
                'amount_20': data.get('amount_20', data.get('amount', 0.0) * 0.2),
                'note': f"Tổng hợp từ {len(data.get('individual_calc_ids', []))} công thức: {data.get('note', '')}",
            })
        
        return self.create(vals_list)

    @api.model
    def create_from_summary_tabs(self, summary_id):
        if not summary_id:
            return False

        summary = self.env['salary.sales.summary'].browse(summary_id)
        if not summary.exists():
            return False

        self.search([('summary_id', '=', summary.id)]).unlink()
        vals_list = []
        ss_employee_ids = summary.sales_commission_employee_ids.mapped('employee_id').ids

        for ss_line in summary.sales_commission_employee_ids:
            team_id = ss_line.employee_id.user_id.sale_team_id.id if ss_line.employee_id.user_id else False
            total_line = summary.total_line_ids.filtered(lambda total: total.team_id.id == team_id)[:1]
            vals_list.append({
                'summary_id': summary.id,
                'result_name': 'Hoa hồng SS',
                'team_id': team_id,
                'employee_id': ss_line.employee_id.id,
                'plan_rate': total_line.achievement_rate if total_line else 0.0,
                'completion_rate': (ss_line.sales_quantity / ss_line.planned_quantity) if ss_line.planned_quantity else 0.0,
                'sales_discount_amount': 0.0,
                'humic_discount_amount': 0.0,
                'amount': ss_line.amount_80 + ss_line.amount_20,
                'amount_80': ss_line.amount_80,
                'amount_20': ss_line.amount_20,
                'note': 'Lấy từ tab Hoa hồng SS',
            })

        for line in summary.personnel_commission_ids:
            if line.employee_id.id in ss_employee_ids:
                continue
            total_line = summary.total_line_ids.filtered(lambda total: total.team_id == line.team_id)[:1]
            amount_80 = line.total_amount_80
            amount_20 = line.total_amount_20
            
            sales_discount_80 = line.sales_discount_80
            sales_discount_20 = line.sales_discount_20
            
            humic_discount_80 = line.humic_discount_80
            humic_discount_20 = line.humic_discount_20
            
            sales_discount_line = summary.sales_discount_ids.filtered(
                lambda d_line: d_line.team_id == line.team_id and line.employee_id in d_line.employee_ids
            )[:1]
            
            humic_discount_line = summary.humic_discount_ids.filtered(
                lambda h_line: h_line.team_id == line.team_id and line.employee_id in h_line.employee_ids
            )[:1]
            
            if sales_discount_line:
                plan_rate = sales_discount_line.rate
            else:
                plan_rate = total_line.achievement_rate if total_line else 0.0
            sales_discount_amount = sales_discount_80 + sales_discount_20
            humic_discount_amount = humic_discount_80 + humic_discount_20
            vals_list.append({
                'summary_id': summary.id,
                'result_name': line.job_title or 'Hoa hồng nhân viên',
                'team_id': line.team_id.id,
                'employee_id': line.employee_id.id,
                'plan_rate': plan_rate,
                'completion_rate': line.allocation_rate,
                'achievement_rate': (
                    total_line.get_sales_discount_achievement_rate()
                    if line.role_sequence == 10 and total_line else 0.0
                ),
                'sales_discount_amount': sales_discount_amount,
                'humic_discount_amount': humic_discount_amount,
                'amount': amount_80 + amount_20,
                'amount_80': amount_80,
                'amount_20': amount_20,
                'note': 'Lấy từ tab Hoa hồng nhân sự khu vực (CKBH từ tab Chiết khấu bán hàng)',
            })

        shared_names = ['Ban lãnh đạo', 'Khối bán hàng', 'Quỹ thưởng', 'Phòng ban khác']
        for name in shared_names:
            sales_lines = summary.sales_discount_ids.filtered(lambda line: line.name == name)
            humic_lines = summary.humic_discount_ids.filtered(lambda line: line.name == name)
            for team in sales_lines.mapped('team_id') | humic_lines.mapped('team_id'):
                team_sales_lines = sales_lines.filtered(lambda line: line.team_id == team)
                team_humic_lines = humic_lines.filtered(lambda line: line.team_id == team)
                sales_discount_amount = sum(team_sales_lines.mapped('total_discount'))
                humic_discount_amount = sum(team_humic_lines.mapped('total_discount'))
                amount_80 = sum(team_sales_lines.mapped('amount_80')) + sum(team_humic_lines.mapped('amount_80'))
                amount_20 = sum(team_sales_lines.mapped('amount_20')) + sum(team_humic_lines.mapped('amount_20'))
                
                plan_rate = team_sales_lines[:1].rate if team_sales_lines else 0.0
                total_line = summary.total_line_ids.filtered(lambda tl: tl.team_id == team)[:1]
                completion_rate = total_line.achievement_rate if total_line else 0.0
                
                vals_list.append({
                    'summary_id': summary.id,
                    'result_name': name,
                    'team_id': team.id,
                    'plan_rate': plan_rate,
                    'completion_rate': completion_rate,
                    'sales_discount_amount': sales_discount_amount,
                    'humic_discount_amount': humic_discount_amount,
                    'amount': amount_80 + amount_20,
                    'amount_80': amount_80,
                    'amount_20': amount_20,
                    'note': 'Tổng hợp từ tab Chiết khấu bán hàng và Chiết khấu Humic',
                })

        if not vals_list:
            return False
        return self.create(vals_list)

    def action_view_calculation(self):
        """Action để xem chi tiết công thức tính toán"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Công thức: {self.calc_id.name}',
            'res_model': 'salary.commission.calculation',
            'res_id': self.calc_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_employee(self):
        """Action để xem chi tiết nhân viên"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Nhân viên: {self.employee_id.name}',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
