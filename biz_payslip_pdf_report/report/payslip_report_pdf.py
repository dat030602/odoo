import json

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class payslip_report_pdf(models.AbstractModel):
    _name = 'report.biz_payslip_pdf_report.payslip_report_pdf'
    _description = 'payslip_report_pdf'

    def get_notice(self):
        return self.env.company.note_payslip

    def get_company_address(self, company):
        address = ''
        if company:
            if company.street:
                address += company.street
            if company.street2:
                address += len(address) > 0 and ', \n' + company.street2 or company.street2
            if company.city:
                address += len(address) > 0 and ', \n' + company.city or company.city
            if company.state_id:
                address += len(address) > 0 and ', \n' + company.state_id.name or company.state_id.name
            if company.country_id:
                address += len(address) > 0 and ', \n' + company.country_id.name or company.country_id.name
        return address


    # def merge_line(self,lines):
        # vals = {}
        # array_categ = []
        # for line in lines.sorted(lambda x: x.salary_rule_id.payslip_no):
        #     if line.category_id.name not in array_categ:
        #         array_categ.append(line.category_id.name)
        # print('4213412412412412',array_categ)
        # for ar in array_categ:
        #
        #     for line in lines.filtered(lambda x: x.category_id.name == ar).sorted(lambda x: x.salary_rule_id.payslip_no):
        #         val = {
        #             'name_category': line.category_id.name,
        #             'index_display': line.salary_rule_id.index_display,
        #             'name': line.salary_rule_id.name,
        #             'rate': line.rate,
        #             'unit': line.salary_rule_id.unit,
        #             'total': line.total,
        #             'print_payslip': line.category_id.print_payslip,
        #             'print_scale': line.category_id.print_scale,
        #             'payslip_no': line.salary_rule_id.payslip_no
        #         }
        #         if line.category_id.name not in vals:
        #             vals[line.category_id.name] = [val]
        #         else:
        #             vals[line.category_id.name].append(val)
        # return vals.items()

    def encode_code(self, code):
        new_code = False
        if code:
            length = len(code) - 2
            new_code = code[0:2] + ("x" * length)
        return new_code


    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'self1': self
        }