from odoo import models, api
from ...models.component import vietnam_number, format_float_number, vietnam_number_upper,format_float_number_weight


class ReportCarRental(models.AbstractModel):
    _name = 'report.ccv_custom_field.rent_proposal_template'
    _description = 'Báo cáo lệnh điều động xe đi công tác'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['approval.request'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'approval.request',
            'docs': docs,
            'vietnam_number': vietnam_number, 
            'format_float_number': format_float_number,
            'vietnam_number_upper': vietnam_number_upper,
            'format_float_number_weight':format_float_number_weight
        }
