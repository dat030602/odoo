from odoo import fields, models, api
from datetime import datetime, timedelta

class StockQuantBackdateWizard(models.TransientModel):
    _name = 'stock.quant.backdate.wizard'
    _inherit = 'abstract.inventory.backdate.wizard'
    _description = 'Stock Quant Backdate Wizard'

    date = fields.Datetime(string='Actual Inspection Date')
    stock_quant_id = fields.Many2one('stock.quant', string="Stock Quant", required=True, ondelete='cascade')


    def process(self):
        self.ensure_one()
        for rec in self:
            date = rec.date + timedelta(hours=7)
            return rec.stock_quant_id.with_context(manual_validate_date_time=rec.date,force_period_date=date).action_apply_inventory()