# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from datetime import datetime

class ProposalForm(models.AbstractModel):
    _name = 'report.biz_ccv_approvals.proposal_form_template'
    _description = 'Proposal Form'
    
    def format_today(self):
        return 'Đồng Nai, ngày %s tháng %s năm %s' % (datetime.today().day, datetime.today().month, datetime.today().year)    
    
    def format_float_number(self, number):
        number_format = ''
        if number:
            if number % 1 == 0:
                number_format = "{:,.0f}".format(number).replace(',', '.')
            else:
                number_format = "{:,.2f}".format(number).rstrip('0').replace(',', '.')
        return number_format
    
    def get_name_CTHĐTV(self):
        name_CTHĐTV = ''
        department = self.env['hr.department'].sudo().search([('name', '=', 'Ban Điều Hành'), ('company_id', '=', self.env.company.id)], limit=1)
        if department:
            name_CTHĐTV = department.manager_id.user_id.name_without_position
        return name_CTHĐTV

    def get_name_BLĐ(self):
        name_BLĐ = ''
        department = self.env['hr.department'].sudo().search([('name', '=', 'Ban Lãnh Đạo'), ('company_id', '=', self.env.company.id)])
        if department:
            name_BLĐ = department.manager_id.user_id.name_without_position
        return name_BLĐ
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['approval.request'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'docs': docs,
            'format_float_number': self.format_float_number,
            'format_today': self.format_today,
            'get_name_CTHĐTV': self.get_name_CTHĐTV,
            'get_name_BLĐ': self.get_name_BLĐ
        }