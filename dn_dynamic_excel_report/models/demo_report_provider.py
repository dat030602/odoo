# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class ExcelReportDemoPartner(models.AbstractModel):
    _name = 'excel.report.demo.partner'
    _inherit = 'excel.report.abstract'
    _description = 'Demo Partner Report Provider'

    @api.model
    def get_report_data(self, records, context=None):
        """
        Return partner data for demo report.
        
        Args:
            records: Partner recordset
            context: Optional context dictionary
            
        Returns:
            List of dictionaries with partner data
        """
        data = []
        for partner in records:
            data.append({
                'name': partner.name or '',
                'email': partner.email or '',
                'phone': partner.phone or '',
                'city': partner.city or '',
                'country': partner.country_id.name if partner.country_id else '',
            })
        return data