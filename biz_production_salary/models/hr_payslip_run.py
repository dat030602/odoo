# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.fields import Command

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    # INSERT_YOUR_CODE
    def action_create_advance_salary_summary(self):
        self.ensure_one()
        AdvanceSalarySummary = self.env['advance.salary.summary']
        payslips = self.slip_ids
        department_ids = payslips.mapped('employee_id.department_id').filtered(lambda d: d)
        for department in department_ids:
            summary = AdvanceSalarySummary.search([
                ('month', '=', str(self.date_start.month) if self.date_start else str(datetime.now().month)),
                ('year', '=', str(self.date_start.year) if self.date_start else str(datetime.now().year)),
                ('department_id', '=', department.id),
            ], limit=1)
            if not summary:
                summary = AdvanceSalarySummary.create({
                    'name': 'Tháng %s/%s - %s' % (str(self.date_start.month) if self.date_start else '', str(self.date_start.year) if self.date_start else '', department.name),
                    'month': str(self.date_start.month) if self.date_start else False,
                    'year': str(self.date_start.year) if self.date_start else False,
                    'department_id': department.id,
                    'advance_date': self.advance_salary_day if self.advance_salary_day else 18,
                })
            employee_ids = summary.line_ids.mapped('employee_id').filtered(lambda e: e.department_id == department)
            employee_ids_not_in_payslip = payslips.mapped('employee_id').filtered(lambda e: e.department_id == department) - employee_ids
            lines = []
            for employee in employee_ids_not_in_payslip:
                payslip = payslips.filtered(lambda p: p.employee_id == employee)
                lines.append(Command.create({
                    'advance_id': summary.id,
                    'employee_id': employee.id,
                    'amount': payslip.line_ids.filtered(lambda l: l.code == 'TTU').total if payslip.line_ids.filtered(lambda l: l.code == 'TTU') else 0.0,
                }))
            payslips_in_dept = payslips.mapped('employee_id').filtered(lambda e: e.department_id == department) - employee_ids_not_in_payslip
            for summary_line_id in summary.line_ids.filtered(lambda l: l.employee_id in payslips_in_dept):
                payslip = payslips.filtered(lambda p: p.employee_id == summary_line_id.employee_id)
                lines.append(Command.update(summary_line_id.id, {
                    'advance_id': summary.id,
                    'amount': payslip.line_ids.filtered(lambda l: l.code == 'TTU').total,
                }))
            summary.write({'line_ids': lines})
        return True
