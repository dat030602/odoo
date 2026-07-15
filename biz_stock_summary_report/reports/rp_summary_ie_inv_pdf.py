from odoo import api, fields, models, _
from datetime import datetime, timedelta

class rp_summary_ie_inv_pdf(models.AbstractModel):
    _name = 'report.biz_stock_summary_report.rp_summary_ie_inv_pdf'
    _description = 'rp_summary_ie_inv_pdf'
    
    def format_float_number(self, num):
        if not num:
            return 0

        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number)
        else:
            number_format = "{:,.2f}".format(number).rstrip('0')
            return number_format
            
    def sum_qty(self, o):
        qty_begin = value_begin = 0
        qty_import = value_import = 0
        qty_export = value_export = 0
        qty_end = value_end = 0

        for line in o.line_ids:
            qty_begin += line.qty_begin
            value_begin += line.value_begin
            qty_import += line.qty_import
            value_import += line.value_import
            qty_export += line.qty_export
            value_export += line.value_export
            qty_end += line.qty_end
            value_end += line.value_end

        return {
            'qty_begin': qty_begin,
            'value_begin': value_begin,
            'qty_import': qty_import,
            'value_import': value_import,
            'qty_export': qty_export,
            'value_export': value_export,
            'qty_end': qty_end,
            'value_end': value_end,
        }

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
        self = self.sudo().with_context(lang='vi_VN')
        doc = self.env['summary.ie.inventory'].browse(docids)
        return {
            'doc_ids': docids,
            'docs':doc,
            'doc_model': 'summary.ie.inventory',
            'format_float_number': self.format_float_number,
            'sum_qty': self.sum_qty,
            'get_company_address': self.get_company_address
        }