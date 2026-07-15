from odoo import fields, models

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'
    
    def _validate_accounting_entries(self):
        """
        This method is used to validate the accounting entries for the stock valuation layers.
        It is used to validate the accounting entries for the stock valuation layers that are related to purchase orders.
        """
        svls = self.filtered(lambda svl: svl.stock_move_id.purchase_line_id)
        return super(StockValuationLayer, self - svls.filtered(
            lambda svl: not (
                svl.stock_move_id.location_id.usage == 'inventory' or
                svl.stock_move_id.location_dest_id.usage == 'inventory'
            )
        ))._validate_accounting_entries()
