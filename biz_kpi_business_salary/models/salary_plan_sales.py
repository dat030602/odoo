from odoo import models, fields, api

class SalaryPlanSales(models.Model):
    _name = 'salary.plan.sales'
    _description = 'Salary Plan Sales'

    name = fields.Char(string='Tên', related='team_id.report_name')
    team_id = fields.Many2one(string='Đội bán hàng', comodel_name='crm.team')
    month = fields.Selection(string='Tháng', selection=[('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'), ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'), ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'), ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12')])
    year = fields.Integer(string='Năm')
    active = fields.Boolean(string='Kích hoạt', default=True)
    progress_compensation_rate = fields.Float(string='Tỷ lệ bù tiến độ (%)', default=0.0)
    
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)
    discount_fund_oc = fields.Monetary(string='Quỹ chiết khấu OC', default=0.0)
    discount_fund_nc = fields.Monetary(string='Quỹ chiết khấu NC', default=0.0)
    discount_fund = fields.Monetary(string='Tổng quỹ chiết khấu', compute='_compute_discount_fund', store=True)

    line_ids = fields.One2many(string='Chi tiết', comodel_name='salary.plan.sales.line', inverse_name='salary_plan_sales_id')

    @api.depends('discount_fund_oc', 'discount_fund_nc')
    def _compute_discount_fund(self):
        for record in self:
            record.discount_fund = record.discount_fund_oc + record.discount_fund_nc
