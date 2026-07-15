# -*- coding: utf-8 -*-

from odoo import api, models
from datetime import datetime, timedelta

class report_business_pdf(models.AbstractModel):
    _name = 'report.biz_profit_loss_statement.report_business_pdf'
    _description = 'report_business_pdf'
    
    def get_lines(self,o):
        res=[]
        no = 0
        for line in o.business_activities_results_line_ids:
            val = {
                    'chi_tieu':line.target_config_id.targets_name,
                    'ma_so':line.code or '',
                    'thuyet_minh':line.present or '',
                    'nam_nay':self.format_float_number(line.this_year),
                    'nam_truoc':self.format_float_number(line.year_ago),
                }

            res.append(val)

        return res

    def format_float_number(self, num):
        if not num:
            return '0'

        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number)
        else:
            return "{:,.2f}".format(number).rstrip('0')

    def format_today(self):
        return 'ngày %s tháng %s năm %s' % (datetime.today().day, datetime.today().month, datetime.today().year)

    def get_company_address(self, company):
        address = ''
        if company:
            if company.street:
                address += company.street
            if company.street2:
                address += len(address) > 0 and ', ' + company.street2 or company.street2
            if company.city:
                address += len(address) > 0 and ', ' + company.city or company.city
            if company.state_id:
                address += len(address) > 0 and ', ' + company.state_id.name or company.state_id.name
            if company.country_id:
                address += len(address) > 0 and ', ' + company.country_id.name or company.country_id.name
        return address

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['business.activities.results'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'business.activities.results',
            'docs': docs,
            'get_lines': self.get_lines,
            'get_company_address': self.get_company_address,
            'format_today': self.format_today
        }

    
