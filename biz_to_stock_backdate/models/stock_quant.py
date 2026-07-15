from odoo import fields, models, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_apply_inventory(self):
        if not self._context.get('manual_validate_date_time') and self.env.user.has_group('to_backdate.group_backdate'):
            view = self.env.ref('biz_to_stock_backdate.stock_quant_view_validate_datetime_manual')
            ctx = dict(self._context or {})
            ctx.update({'default_stock_quant_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.quant.backdate.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': ctx,
            }
        res = super(StockQuant, self).action_apply_inventory()  

        if self._context.get("manual_validate_date_time", False):
            manual_validate_date_time = self._context.get('manual_validate_date_time', False)

            for quant in self:
                product_uom = quant.product_uom_id

                domain = [
                    ("date",'>', manual_validate_date_time),
                    ("product_id",'=', quant.product_id.id),
                    ("state",'=', 'done')
                ]
                if quant.lot_id:
                    domain += [('lot_id','=', quant.lot_id.id)]

                domain_in = domain + [("location_dest_id",'=', quant.location_id.id)]
                # quant_move_in = sum(move_in.mapped("qty_done"))
                move_in = quant.env['stock.move.line'].search(domain_in)
                quant_move_in = 0
                for move in move_in:
                    quant_move_in += move.product_uom_id._compute_quantity(move.qty_done, product_uom, rounding_method='HALF-UP')

                if quant_move_in:
                    quant.write({
                        'quantity': quant.quantity + quant_move_in
                    })

                domain_out = domain + [("location_id",'=', quant.location_id.id)]
                move_out = quant.env['stock.move.line'].search(domain_out)
                quant_move = 0
                for move in move_out:
                    quant_move += move.product_uom_id._compute_quantity(move.qty_done, product_uom, rounding_method='HALF-UP')

                if quant_move:
                    quant.write({
                        'quantity': quant.quantity - quant_move
                    })

        return res