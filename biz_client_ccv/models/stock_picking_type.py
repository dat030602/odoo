# -*- coding: utf-8 -*-


from odoo import models, api
from odoo.osv import expression


class StockWarehouse(models.Model):
    _inherit = "stock.picking.type"

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self.env.user and self.env.user.stock_warehouse_ids:
            args = expression.AND([[("warehouse_id", 'in', self.env.user.stock_warehouse_ids.ids)], args])
        return super(StockWarehouse, self)._name_search(name, args, operator, limit, name_get_uid)