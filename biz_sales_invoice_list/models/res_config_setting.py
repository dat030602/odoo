from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remove_customer_reports = fields.Boolean(
        related='company_id.remove_customer_reports',
        string="Remove Customer Reports", 
        readonly=False,
        help="If checked, reports including customer will be removed."
    )