from odoo import models, fields, api


class SalaryHumicDiscount(models.Model):
    """Humic discount allocation by team."""
    _name = 'salary.humic.discount'
    _description = 'Salary Humic Discount'
    _order = 'team_id, sequence, id'

    DEFAULT_TEAM_NAMES = ['Khu vực 1', 'Khu vực 2', 'Khu vực 3', 'Khu vực 4', 'Khu vực 5']
    DEFAULT_LINES = [
        ('leadership', 'Ban lãnh đạo', 0.10),
        ('other_department', 'Phòng ban khác', 0.10),
        ('bonus_fund', 'Quỹ thưởng', 0.15),
        ('area_manager', 'Trưởng khu vực nhận từ quỹ chung', 0.20),
        ('personal_sales', 'Nhân viên nhận do cá nhân bán', 0.45),
    ]

    name = fields.Char(string='Công thức tính toán', required=True)
    sequence = fields.Integer(default=10)
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', required=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        'salary_humic_discount_employee_rel',
        'discount_id',
        'employee_id',
        string='Nhân viên áp dụng',
    )
    discount_fund = fields.Monetary(
        string='Tổng tiền hoa hồng Humic',
        compute='_compute_amounts',
        store=True,
    )
    rate = fields.Float(string='Tỷ lệ', digits=(16, 4), required=True)
    total_discount = fields.Monetary(string='Tổng chiết khấu', compute='_compute_amounts', store=True)
    amount_80 = fields.Monetary(string='Thực nhận 80%', compute='_compute_amounts', store=True)
    amount_20 = fields.Monetary(string='Giữ lại 20%', compute='_compute_amounts', store=True)
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')

    @api.depends(
        'rate',
        'summary_id.humic_sales_detail_ids.team_id',
        'summary_id.humic_sales_detail_ids.commission_amount',
    )
    def _compute_amounts(self):
        for record in self:
            humic_lines = record.summary_id.humic_sales_detail_ids.filtered(
                lambda line: line.team_id == record.team_id
            )
            record.discount_fund = sum(humic_lines.mapped('commission_amount'))
            record.total_discount = record.discount_fund * record.rate
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
        for team_name in self.DEFAULT_TEAM_NAMES:
            team = self.env['crm.team'].search([
                '|',
                ('report_name', '=', team_name),
                ('name', '=', team_name),
            ], limit=1)
            if not team:
                continue

            humic_lines = summary.humic_sales_detail_ids.filtered(lambda line: line.team_id == team)
            humic_users = humic_lines.mapped('user_id')
            humic_employees = self.env['hr.employee'].search([
                ('user_id', 'in', humic_users.ids),
            ]) if humic_users else self.env['hr.employee']
            area_manager_employees = self.env['hr.employee'].search([
                ('user_id', '=', team.user_id.id),
            ]) if team.user_id else self.env['hr.employee']

            for index, (code, label, rate) in enumerate(self.DEFAULT_LINES, start=1):
                vals = {
                    'summary_id': summary.id,
                    'team_id': team.id,
                    'name': label,
                    'sequence': index * 10,
                    'rate': rate,
                }
                if code == 'area_manager' and area_manager_employees:
                    vals['employee_ids'] = [(6, 0, area_manager_employees.ids)]
                elif code == 'personal_sales' and humic_employees:
                    vals['employee_ids'] = [(6, 0, humic_employees.ids)]
                vals_list.append(vals)

        if not vals_list:
            return False

        return self.create(vals_list)
