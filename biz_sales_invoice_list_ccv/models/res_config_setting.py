from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remove_customer_reports_ccv = fields.Boolean(
        related='company_id.remove_customer_reports_ccv',
        string="Remove Customer Reports CCV", 
        readonly=False,
        help="If checked, reports including customer will be removed."
    )