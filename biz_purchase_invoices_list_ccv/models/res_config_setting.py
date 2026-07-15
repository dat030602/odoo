from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remove_supplier_reports_ccv = fields.Boolean(
        related='company_id.remove_supplier_reports_ccv',
        string="Remove Supplier Reports CCV", 
        readonly=False,
        help="If checked, reports including suppliers will be removed."
    )