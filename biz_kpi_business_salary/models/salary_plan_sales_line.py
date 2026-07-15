from odoo import models, fields

class SalaryPlanSalesLine(models.Model):
    _name = 'salary.plan.sales.line'
    _description = 'Salary Plan Sales Line'

    salary_plan_sales_id = fields.Many2one(string='Salary Plan Sales', comodel_name='salary.plan.sales')
    
    # Kế thừa cũ (Giữ lại để không lỗi)
    state_ids = fields.Many2many(string='Tỉnh/Thành phố', comodel_name='res.country.state')
    
    # Trường mới thêm cho cấu trúc Kế hoạch Doanh số mới
    target_type = fields.Selection(string='Loại chỉ tiêu', selection=[
        ('state', 'Tỉnh/Thành phố'),
        ('oc', 'Khách hàng cũ (OC)'),
        ('nc', 'Khách hàng mới (NC)'),
        ('employee', 'Nhân viên')
    ], default='state', required=True)
    employee_id = fields.Many2one(string='Nhân viên', comodel_name='hr.employee')
    target_code = fields.Char(string='Mã định danh (OC/NC/NV)')
    
    quantity = fields.Float(string='Mục tiêu', digits="Product Unit of Measure")
    active = fields.Boolean(string='Kích hoạt', related='salary_plan_sales_id.active')
