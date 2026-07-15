from odoo import fields, models, api
from datetime import datetime, timedelta


class StockInventoryBackdateWizard(models.TransientModel):
    _name = 'mrp.production.backdate.wizard'
    _inherit = 'abstract.inventory.backdate.wizard'
    _description = 'Stock Inventory Backdate Wizard'

    date = fields.Datetime(string='Inventory Date')
    mrp_production_id = fields.Many2one('mrp.production', string="MRP Production", required=True, ondelete='cascade')


    def process(self):
        self.ensure_one()
        date = self.date + timedelta(hours=7)
        # put force_period_date into context so that account move can take this date as accounting date also
        return self.mrp_production_id.with_context(manual_validate_date_time=self.date,force_period_date=date).sudo().button_mark_done()
