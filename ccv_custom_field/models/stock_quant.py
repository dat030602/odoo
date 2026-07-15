from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_reset_quantity(self):
        self.env.cr.execute("""
            select 'OUT', sum(quantity_done) from stock_move
            where state='done' and location_id=8
            UNION ALL
            select 'IN', sum(quantity_done) from stock_move
            where state='done' and location_dest_id=8
        """)
        result = self.env.cr.fetchall()
        inventory_quantity = 0
        for item in result:
            if item[0] == 'IN':
                inventory_quantity += float(item[2])
            elif item[0] == 'OUT':
                inventory_quantity -= float(item[2])
        self.inventory_quantity = inventory_quantity
        self.inventory_diff_quantity = 0
        self.inventory_quantity_set = False
