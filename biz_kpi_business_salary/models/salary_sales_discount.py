from odoo import models, fields, api


class SalarySalesDiscount(models.Model):
    """Sales discount allocation by team."""
    _name = 'salary.sales.discount'
    _description = 'Salary Sales Discount'
    _order = 'team_id, sequence, id'

    DEFAULT_TEAM_FUNDS = {
        'Khu vực 1': 35472536.0,
        'Khu vực 2': 0.0,
        'Khu vực 3': 11132500.0,
        'Khu vực 4': 10232200.0,
        'Khu vực 5': 9833450.0,
    }
    DEFAULT_LINES = [
        ('leadership', 'Ban lãnh đạo', 0.10),
        ('area_manager', 'Trưởng khu vực', 0.45),
        ('sales_department', 'Khối bán hàng', 0.25),
        ('other_department', 'Phòng ban khác', 0.10),
        ('bonus_fund', 'Quỹ thưởng', 0.10),
    ]

    name = fields.Char(string='Công thức tính toán', required=True)
    sequence = fields.Integer(default=10)
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', required=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        'salary_sales_discount_employee_rel',
        'discount_id',
        'employee_id',
        string='Nhân viên áp dụng',
    )
    team_discount_fund_oc = fields.Monetary(string='Tổng quỹ OC khu vực')
    team_discount_fund_nc = fields.Monetary(string='Tổng quỹ NC khu vực')
    team_discount_fund = fields.Monetary(string='Tổng quỹ chiết khấu khu vực')
    
    rate = fields.Float(string='Tỷ lệ', digits=(16, 4), required=True)
    
    discount_fund_oc = fields.Monetary(string='Quỹ chiết khấu OC', compute='_compute_amounts', store=True)
    discount_fund_nc = fields.Monetary(string='Quỹ chiết khấu NC', compute='_compute_amounts', store=True)
    total_discount = fields.Monetary(string='Tổng chiết khấu', compute='_compute_amounts', store=True)
    
    amount_80 = fields.Monetary(string='Thực nhận 80%', compute='_compute_amounts', store=True)
    amount_20 = fields.Monetary(string='Giữ lại 20%', compute='_compute_amounts', store=True)
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')

    @api.depends('team_discount_fund_oc', 'team_discount_fund_nc', 'rate')
    def _compute_amounts(self):
        for record in self:
            record.discount_fund_oc = record.team_discount_fund_oc * record.rate
            record.discount_fund_nc = record.team_discount_fund_nc * record.rate
            record.total_discount = record.discount_fund_oc + record.discount_fund_nc
            record.amount_80 = record.total_discount * 0.8
            record.amount_20 = record.total_discount - record.amount_80

    @api.model
    def create_default_lines(self, summary_id):
        if not summary_id:
            return False

        summary = self.env['salary.sales.summary'].browse(summary_id)
        if not summary.exists():
            return False

        self.search([('summary_id', '=', summary.id)]).unlink()

        vals_list = []
        for team_name, default_fund in self.DEFAULT_TEAM_FUNDS.items():
            team = self.env['crm.team'].search([
                '|',
                ('report_name', '=', team_name),
                ('name', '=', team_name),
            ], limit=1)
            if not team:
                continue

            area_manager_employees = self.env['hr.employee'].search([
                ('user_id', '=', team.user_id.id),
            ]) if team.user_id else self.env['hr.employee']

            # Retrieve funds from salary.plan.sales
            plan = self.env['salary.plan.sales'].search([
                ('month', '=', summary.month),
                ('year', '=', summary.year),
                ('team_id', '=', team.id)
            ], limit=1)
            
            fund_oc = plan.discount_fund_oc if plan else 0.0
            fund_nc = plan.discount_fund_nc if plan else 0.0
            total_fund = fund_oc + fund_nc

            for index, (code, label, rate) in enumerate(self.DEFAULT_LINES, start=1):
                vals = {
                    'summary_id': summary.id,
                    'team_id': team.id,
                    'name': label,
                    'sequence': index * 10,
                    'team_discount_fund_oc': fund_oc,
                    'team_discount_fund_nc': fund_nc,
                    'team_discount_fund': total_fund,
                    'rate': rate,
                }
                if code == 'area_manager' and area_manager_employees:
                    vals['employee_ids'] = [(6, 0, area_manager_employees.ids)]
                vals_list.append(vals)

        if not vals_list:
            return False

        return self.create(vals_list)
