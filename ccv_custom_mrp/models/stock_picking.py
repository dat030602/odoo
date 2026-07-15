# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_transfer_to_consignment(self):
        self.ensure_one()
        # Tìm kho ký gửi (Warehouse 60)
        warehouse_60 = self.env['stock.warehouse'].browse(60)
        if not warehouse_60.exists() or not warehouse_60.lot_stock_id:
            raise UserError(_('Không tìm thấy Kho Ký gửi (ID=60) hoặc kho này chưa có địa điểm kho.'))
        
        consignment_location = warehouse_60.lot_stock_id

        # Update note
        note_str = "Chuyển kho ký gửi"
        if self.note:
            if note_str not in self.note:
                self.note = f"{self.note}\n{note_str}"
        else:
            self.note = note_str
            
        # Add log to chatter
        self.message_post(body=_("Đã chuyển vị trí nguồn sang Kho Ký Gửi (KKG)."))

        # If picking is not done, just update the fields normally
        if self.state not in ('done', 'cancel'):
            self.location_id = consignment_location.id
            for move in self.move_ids:
                move.location_id = consignment_location.id
                for line in move.move_line_ids:
                    line.location_id = consignment_location.id
        else:
            # If picking is done, force update
            old_location = self.location_id
            
            # Update picking
            self.env.cr.execute("UPDATE stock_picking SET location_id=%s WHERE id=%s", (consignment_location.id, self.id))
            
            for move in self.move_ids:
                if move.state == 'done':
                    # Update stock moves
                    self.env.cr.execute("UPDATE stock_move SET location_id=%s WHERE id=%s", (consignment_location.id, move.id))
                    self.env.cr.execute("UPDATE stock_move_line SET location_id=%s WHERE move_id=%s", (consignment_location.id, move.id))
                    self.env.cr.execute("UPDATE stock_valuation_layer SET location_id=%s WHERE stock_move_id=%s", (consignment_location.id, move.id))
                    
                    # Reverse stock logic: 
                    # The delivery order deducted stock from old_location and added to location_dest_id.
                    # Since we change source from old_location to consignment_location:
                    # We must ADD back to old_location, and SUBTRACT from consignment_location.
                    self.env['stock.quant']._update_available_quantity(move.product_id, old_location, move.product_uom_qty)
                    self.env['stock.quant']._update_available_quantity(move.product_id, consignment_location, -move.product_uom_qty)
                    
                    move.invalidate_recordset(['location_id'])
                    move.move_line_ids.invalidate_recordset(['location_id'])
            
            self.invalidate_recordset(['location_id'])

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
