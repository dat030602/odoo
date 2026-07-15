from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remove_supplier_reports = fields.Boolean(
        related='company_id.remove_supplier_reports',
        string="Remove Supplier Reports", 
        readonly=False,
        help="If checked, reports including suppliers will be removed."
    )