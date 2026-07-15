from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date

class SalaryPaymentListWizard(models.TransientModel):
    _name = 'salary.payment.list.wizard'
    _description = 'Salary Payment List'

    month = fields.Selection(
        selection=[(str(i), f"{i:02}") for i in range(1, 13)],
        string="Tháng",
        required=True
    )
    year = fields.Selection(
        selection=[(str(y), str(y)) for y in range(2020, 2031)],
        string="Năm",
        required=True
    )
    advance_salary = fields.Boolean(string="Lương ứng")
    department_ids = fields.Many2many('hr.department',string="Phòng ban")
    voter_id = fields.Many2one('res.users',string="Người lập")
    chief_finance_id = fields.Many2one('res.users',string="Phòng Kế toán")
    human_resources_dept_id = fields.Many2one('res.users',string="Phòng HCNS")
    director_id  = fields.Many2one('res.users',string="Thủ trưởng đơn vị")

    @api.model
    def default_get(self, fields_list):
        defaults = super(SalaryPaymentListWizard, self).default_get(fields_list)

        today = date.today()
        current_month = str(today.month)
        current_year = str(today.year)

        defaults.update({
            'month': current_month,
            'year': current_year,
            'voter_id': self.env.user.id,
        })
        return defaults

    def action_generate_report(self):
        return self.env.ref('ccv_bao_cao.salary_payment_list_report').report_action(self,
            data={
                'month': self.month,
                'year': self.year,
                'advance_salary': self.advance_salary,
                'department_ids': self.department_ids.ids,
                'voter_id': self.voter_id.id,
                'chief_finance_id': self.chief_finance_id.id,
                'human_resources_dept_id': self.human_resources_dept_id.id,
                'director_id': self.director_id.id,
            })
