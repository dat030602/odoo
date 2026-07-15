from odoo import fields, models
from datetime import datetime, timedelta


class StockPickingValidateManualTime(models.TransientModel):
    _name = 'stock.picking.validate.manual.datetime.wizard'
    _inherit = 'abstract.inventory.backdate.wizard'
    _description = 'Stock Transfer Backdate Wizard'

    date = fields.Datetime(string='Transfer Date')
    picking_id = fields.Many2one('stock.picking', string="Transfer", required=True, ondelete='cascade')

    def process(self):
        self.ensure_one()
        # put force_period_date into context so that account move can take this date as accounting date also
        date = self.date + timedelta(hours=7)
        return self.picking_id.with_context(manual_validate_date_time=self.date, force_period_date=date).button_validate()
