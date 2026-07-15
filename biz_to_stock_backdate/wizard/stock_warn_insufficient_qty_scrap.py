from odoo import fields, models
from datetime import datetime, timedelta


class StockWarnInsufficientQtyScrap(models.TransientModel):
    _inherit = 'stock.warn.insufficient.qty.scrap'

    scrap_backdate = fields.Datetime(string='Scrap Backdate')

    def action_done(self):
        if self.scrap_backdate:
            date =  self.scrap_backdate + timedelta(hours=7)
            return super(StockWarnInsufficientQtyScrap, self.with_context(
                manual_validate_date_time=self.scrap_backdate,
                force_period_date=date)).action_done()
        return super(StockWarnInsufficientQtyScrap, self).action_done()
