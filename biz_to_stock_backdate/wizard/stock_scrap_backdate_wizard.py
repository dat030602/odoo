from odoo import fields, models

from datetime import datetime, timedelta

class StockScrapBackdateWizard(models.TransientModel):
    _name = 'stock.scrap.backdate.wizard'
    _inherit = 'abstract.inventory.backdate.wizard'
    _description = 'Stock Scrap Backdate Wizard'

    date = fields.Datetime(string='Actual Scrap Date')
    scrap_id = fields.Many2one('stock.scrap', string="Stock Scrap", required=True, ondelete='cascade')

    def process(self):
        self.ensure_one()
        date = self.date + timedelta(hours=7)
        self.scrap_id.write({'date_expected': self.date})
        return self.scrap_id.with_context(
            manual_validate_date_time=self.date,
            force_period_date=date
            ).action_validate()
