# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if options.get('toolbar'):
            for view_type in res['views']:
                res['views'][view_type]['toolbar'].update({'print': [{'id': self.env.ref('biz_payslip_excel_report.action_report_salary_slip_excel').id, 'name': (_('Salary Slip (Excel)')), 'binding_view_types': 'list,form'}]})
        return res