from odoo import models, fields, api

class StockPickingValidateManualTime(models.TransientModel):
    _inherit = 'stock.picking.validate.manual.datetime.wizard'

    def process(self):
        res = super(StockPickingValidateManualTime, self).process()
        if self.picking_id.need_create_invoice and self.picking_id.purchase_id:
            a = self.picking_id.action_create_invoice()
        return res