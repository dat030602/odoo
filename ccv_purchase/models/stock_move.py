from odoo import fields, models

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    def _is_purchase_return(self):
        res = super(StockMove,self)._is_purchase_return()
        res = self.location_dest_id.usage in ("supplier", "inventory")
        return res

    def _prepare_common_svl_vals(self):
        res = super(StockMove,self)._prepare_common_svl_vals()
        description = self.reference and '%s - %s' % (self.reference, self.product_id.display_name) or self.product_id.display_name
        if self.sudo().picking_id.purchase_id or self.sudo().picking_id.purchase_order_id:
            purchase = self.picking_id.purchase_id or self.picking_id.purchase_order_id
            if purchase.custom_declaration_number:
                description += f" - STK {purchase.custom_declaration_number}"
        res.update({'description': description})
        return res
        
