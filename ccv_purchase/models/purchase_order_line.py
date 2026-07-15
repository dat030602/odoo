from odoo import fields, models, api, _
from odoo.exceptions import UserError
import datetime
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    @api.onchange('price_tax','price_subtotal')
    def _onchange_price_tax(self):
        for rec in self:
            rec.price_total = rec.price_subtotal + rec.price_tax

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_received(self):
        super(PurchaseOrderLine, self)._compute_qty_received()
        for line in self:
            if line.qty_received_method == 'stock_moves':
                total = line.qty_received
                for move in line._get_po_line_moves():
                    if move.state == 'done':
                        # In Odoo 15, the base method adds any move that is not a purchase return.
                        # This includes internal transfers or inventory adjustments linked via custom scripts.
                        # We must revert the incorrectly added quantities for any move not originating from a supplier.
                        is_purchase_return = move._is_purchase_return()
                        is_dropship_return = move.origin_returned_move_id and move.origin_returned_move_id._is_dropshipped() and not move._is_dropshipped_returned()
                        is_refund_return = move.origin_returned_move_id and move.origin_returned_move_id._is_purchase_return() and not move.to_refund
                        
                        if not is_purchase_return and not is_dropship_return and not is_refund_return:
                            if move.location_id.usage not in ('supplier', 'inventory'):
                                total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                line.qty_received = total


    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        if 'price_tax' in vals or 'price_subtotal' in vals:
            self._onchange_price_tax()
            self.order_id._amount_all()
        return res

    
    def recompute_exchange_rate_svl(self, rate=None):
        for rec in self:
            if rate is None:
                rate = rec.order_id.manual_currency_exchange_rate if rec.order_id.apply_manual_currency_exchange else 1
            sms = rec.move_ids.filtered(lambda x: x.state not in ['cancel'])
            for sm in sms:
                sm.price_unit = rec.price_unit * rate
                svls = sm.stock_valuation_layer_ids.sudo()
                for svl in svls:
                    value_import = sm.price_unit * svl.quantity
                    svl.write({
                        'unit_cost_float': sm.price_unit,
                        'value_import': value_import
                    })
                    svl.sudo().action_update_value()

# Trigger deploy
