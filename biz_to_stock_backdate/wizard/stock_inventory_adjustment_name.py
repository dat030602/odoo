from odoo import fields, models, api
from datetime import datetime, timedelta


class StockInventoryAdjustmentName(models.TransientModel):
    _inherit = 'stock.inventory.adjustment.name'

    inventory_adjustment_date = fields.Datetime(string='Actual Inspection Date', default=fields.Datetime.now)

    def action_apply(self):
        date = self.inventory_adjustment_date + timedelta(hours=7)
        self = self.with_context(manual_validate_date_time=self.inventory_adjustment_date,force_period_date=date)
        return super(StockInventoryAdjustmentName, self).action_apply()
