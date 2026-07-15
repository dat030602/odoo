# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    value_import = fields.Float('Value import',copy=False)
    run_import_value = fields.Boolean(copy=False)

    # def _apply_inventory(self):
    #     if self._context.get('run_import_value'):
    #         self = self.with_context(value_import=self.value_import)
    #         self.run_import_value = True
    #     return super(StockQuant, self)._apply_inventory()

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity','run_import_value')
    def _compute_value(self):
        super(StockQuant,self)._compute_value()
        for quant in self.filtered(lambda x: x.run_import_value):
            quant.value = quant.value_import

    def action_update_company(self):
        for res in self:
            res.company_id = self.env.company