from odoo import models, fields, api
import logging
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = "mrp.production"
    
    product_image_1920 = fields.Image(related='product_id.image_1920', string="Ảnh sản phẩm", readonly=True)
    product_packaging_image = fields.Image(related='product_id.product_tmpl_id.packaging_image', string="Hình ảnh bao bì", readonly=True)

    def button_mark_done(self):
        self = self.sudo()
        return super(MrpProduction, self.sudo().with_context(skip_immediate=True, manual_validate_date_time=self.stock_date_receipt)).button_mark_done()
    
    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        if self.picking_type_id and self.picking_type_id.sequence_id:
            self.name = self.picking_type_id.sequence_id.next_by_id()

    def action_remove_internal_picking(self, location_src_id, location_dest_id):
        cr = self.env.cr

        for mrp in self:
            to_run = True
            move_raw_ids = mrp.move_raw_ids
            picking_ids = mrp.picking_ids.filtered(lambda p: p.state == 'done')
            for move_raw in move_raw_ids:
                location_ids = picking_ids.move_ids.filtered(lambda m: m.state == 'done' and m.product_id == move_raw.product_id).mapped('location_id') - location_src_id
                if not location_ids.exists() or len(location_ids) == 1 or location_ids.filtered(lambda l: l.warehouse_id.id == 5).exists():
                    continue
                to_run = False
                break
            if not to_run:
                continue
            cr.execute("""
                UPDATE mrp_production
                SET location_src_id = %s, location_dest_id = %s
                WHERE id = %s
            """, (location_src_id.id, location_dest_id.id, mrp.id))
            location_run = {}
            for move_raw in move_raw_ids:
                location_ids = picking_ids.move_ids.filtered(lambda m: m.state == 'done' and m.product_id == move_raw.product_id).mapped('location_id')
                location_id = self.env['stock.location']
                if len(location_ids) == 1:
                    location_id = location_ids
                elif location_ids.filtered(lambda l: l.warehouse_id.id == 5):
                    location_id = location_ids.filtered(lambda l: l.warehouse_id.id == 5)
                elif len(location_ids.filtered(lambda l: l != location_src_id)) == 1:
                    location_id = location_ids.filtered(lambda l: l != location_src_id)

                if not location_id:
                    continue
                
                # Update stock.move using SQL
                cr.execute("""
                    UPDATE stock_move
                    SET location_id = %s
                    WHERE id = %s
                """, (location_id.id, move_raw.id))
                # Update stock.move.line using SQL
                for move_line in move_raw.move_line_ids:
                    cr.execute("""
                        UPDATE stock_move_line
                        SET location_id = %s
                        WHERE id = %s
                    """, (location_id.id, move_line.id))
                
                # Update stock.valuation.layer using SQL
                for valuation_layer in move_raw.stock_valuation_layer_ids:
                    cr.execute("""
                        UPDATE stock_valuation_layer
                        SET location_id = %s
                        WHERE id = %s
                    """, (location_id.id, valuation_layer.id))
                location_run[move_raw.product_id.id] = location_id.id
                
            move_finished_ids = mrp.move_finished_ids
            for move_finished in move_finished_ids:
                # Update stock.move using SQL
                cr.execute("""
                    UPDATE stock_move
                    SET location_dest_id = %s
                    WHERE id = %s
                """, (location_dest_id.id, move_finished.id))
                
                # Update stock.move.line using SQL
                for move_line in move_finished.move_line_ids:
                    cr.execute("""
                        UPDATE stock_move_line
                        SET location_dest_id = %s
                        WHERE id = %s
                    """, (location_dest_id.id, move_finished.id))
                
                # Update stock.valuation.layer using SQL
                for valuation_layer in move_finished.stock_valuation_layer_ids:
                    cr.execute("""
                        UPDATE stock_valuation_layer
                        SET location_dest_id = %s
                        WHERE id = %s
                    """, (location_dest_id.id, valuation_layer.id))
            
            unbuild_ids = self.env['mrp.unbuild'].search([('mo_id', '=', mrp.id)])
            for unbuild in unbuild_ids:
                unbuild.write({
                    'location_id': location_src_id.id,
                    'location_dest_id': location_dest_id.id,
                })
                move_unbuild_ids = self.env['stock.move'].search([('unbuild_id', '=', unbuild.id)])
                # Nguyên liệu
                for move_unbuild in move_unbuild_ids.filtered(lambda m: m.state == 'done' and m.location_id.usage == 'production'):
                    # Update stock.move using SQL
                    location_id = location_run.get(move_unbuild.product_id.id, False)
                    if not location_id:
                        continue
                    cr.execute("""
                        UPDATE stock_move
                        SET location_dest_id = %s
                        WHERE id = %s
                    """, (location_id, move_unbuild.id))
                    
                    # Update stock.move.line using SQL
                    for move_line in move_unbuild.move_line_ids:
                        cr.execute("""
                            UPDATE stock_move_line
                            SET location_dest_id = %s
                            WHERE id = %s
                        """, (location_id, move_line.id))
                        cr.execute("""
                            UPDATE stock_move
                            SET location_dest_id = %s
                            WHERE id = %s
                        """, (location_id, move_line.move_id.id))
                    
                    # Update stock.valuation.layer using SQL
                    for valuation_layer in move_unbuild.stock_valuation_layer_ids:
                        cr.execute("""
                            UPDATE stock_valuation_layer
                            SET location_dest_id = %s
                            WHERE id = %s
                        """, (location_id, valuation_layer.id))

                # Thành phẩm
                for move_unbuild in move_unbuild_ids.filtered(lambda m: m.state == 'done' and m.location_dest_id.usage == 'production'):
                    # Update stock.move using SQL
                    cr.execute("""
                        UPDATE stock_move
                        SET location_id = %s
                        WHERE id = %s
                    """, (location_dest_id.id, move_unbuild.id))
                    
                    # Update stock.move.line using SQL
                    for move_line in move_unbuild.move_line_ids:
                        cr.execute("""
                            UPDATE stock_move_line
                            SET location_id = %s
                            WHERE id = %s
                        """, (location_dest_id.id, move_line.id))
                        cr.execute("""
                            UPDATE stock_move
                            SET location_id = %s
                            WHERE id = %s
                        """, (location_dest_id.id, move_line.move_id.id))
                    
                    # Update stock.valuation.layer using SQL
                    for valuation_layer in move_unbuild.stock_valuation_layer_ids:
                        cr.execute("""
                            UPDATE stock_valuation_layer
                            SET location_id = %s
                            WHERE id = %s
                        """, (location_dest_id.id, valuation_layer.id))

            picking_ids.move_ids.move_line_ids.write({
                'state': 'draft',
            })
            picking_ids.move_ids.write({
                'state': 'draft',
            })
            picking_ids.move_ids.stock_valuation_layer_ids.sudo().action_delete_layer()
            picking_ids.unlink()
