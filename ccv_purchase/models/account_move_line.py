from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    def _apply_price_difference(self):
        return self.env['stock.valuation.layer'].sudo(), self.env['account.move.line'].sudo()
