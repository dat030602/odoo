from odoo import models, fields, api

class AlphaReport(models.TransientModel):
    _inherit = 'alpha.report'

    def action_print_receivables_report(self):
        return self.env.ref('ccv_report_debt.customer_receivables_report_pdf').report_action(self)

