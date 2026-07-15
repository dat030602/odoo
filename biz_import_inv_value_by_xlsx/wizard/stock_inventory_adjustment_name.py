from odoo import fields, models, api
from datetime import datetime, timedelta


class StockInventoryAdjustmentName(models.TransientModel):
    _inherit = 'stock.inventory.adjustment.name'

    run_import_value = fields.Boolean('Run by import value')

    def action_apply(self):
        self = self.with_context(run_import_value=True)
        return super(StockInventoryAdjustmentName, self).action_apply()
