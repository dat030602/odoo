from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MrpProductionConsignmentWizard(models.TransientModel):
    _name = 'mrp.production.consignment.wizard'
    _description = 'Wizard to transfer to Consignment Location'

    production_ids = fields.Many2many('mrp.production', string='Lệnh sản xuất')
    is_multi = fields.Boolean(compute='_compute_is_multi')
    
    product_id = fields.Many2one('product.product', string='Sản phẩm', compute='_compute_production_info')
    total_qty = fields.Float(string='Tổng số lượng', compute='_compute_production_info')
    
    consignment_qty = fields.Float(string='Số lượng Ký gửi', default=0.0)
    stock_qty = fields.Float(string='Số lượng Kho TP', compute='_compute_stock_qty')
    
    apply_all = fields.Boolean(string='Chuyển toàn bộ (100%)', default=False, 
                               help='Nếu tích chọn, hệ thống sẽ chuyển toàn bộ số lượng thành phẩm sang Kho ký gửi cho tất cả các lệnh đã chọn.')

    @api.depends('production_ids')
    def _compute_is_multi(self):
        for rec in self:
            rec.is_multi = len(rec.production_ids) > 1

    @api.depends('production_ids')
    def _compute_production_info(self):
        for rec in self:
            if len(rec.production_ids) == 1:
                rec.product_id = rec.production_ids.product_id
                rec.total_qty = rec.production_ids.product_qty
            else:
                rec.product_id = False
                rec.total_qty = 0.0

    @api.depends('total_qty', 'consignment_qty', 'apply_all', 'is_multi')
    def _compute_stock_qty(self):
        for rec in self:
            if rec.apply_all or rec.is_multi:
                rec.stock_qty = 0.0
            else:
                rec.stock_qty = rec.total_qty - rec.consignment_qty

    def action_apply_consignment(self):
        self.ensure_one()
        # Find Consignment Location (Warehouse ID 60)
        warehouse_60 = self.env['stock.warehouse'].browse(60)
        if not warehouse_60.exists() or not warehouse_60.lot_stock_id:
            raise UserError(_('Không tìm thấy Kho Ký gửi (ID=60) hoặc kho này chưa có địa điểm kho.'))
        
        consignment_location = warehouse_60.lot_stock_id

        for production in self.production_ids:
            # Determine qty for this production
            if self.apply_all or self.is_multi:
                qty_to_consignment = production.product_qty
            else:
                qty_to_consignment = self.consignment_qty
            
            if qty_to_consignment <= 0:
                continue
            if qty_to_consignment > production.product_qty:
                raise UserError(_('Số lượng ký gửi không được vượt quá tổng số lượng của Lệnh sản xuất %s.') % production.name)
            
            production.consignment_location_id = consignment_location.id
            if production.state != 'done':
                # Split stock.move of finished product
                for move in production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id and m.state not in ('done', 'cancel') and m.location_dest_id != consignment_location):
                    if qty_to_consignment == move.product_uom_qty:
                        move.location_dest_id = consignment_location.id
                    else:
                        # Create a new move for consignment
                        new_move_vals = move.copy_data({
                            'product_uom_qty': qty_to_consignment,
                            'location_dest_id': consignment_location.id,
                        })[0]
                        self.env['stock.move'].create(new_move_vals)
                        # Decrease current move
                        move.product_uom_qty -= qty_to_consignment
            else:
                # Ép chia dòng cho lệnh Đã Hoàn Thành (không tạo phiếu nội bộ)
                for move in production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id and m.state == 'done' and m.location_dest_id != consignment_location):
                    if qty_to_consignment == move.product_uom_qty:
                        # Chuyển toàn bộ: chỉ đổi location_dest_id
                        old_location = move.location_dest_id
                        self.env.cr.execute("UPDATE stock_move SET location_dest_id=%s WHERE id=%s", (consignment_location.id, move.id))
                        self.env.cr.execute("UPDATE stock_move_line SET location_dest_id=%s WHERE move_id=%s", (consignment_location.id, move.id))
                        
                        # Fix SVL location
                        if 'location_dest_id' in self.env['stock.valuation.layer']._fields:
                            self.env.cr.execute("UPDATE stock_valuation_layer SET location_dest_id=%s WHERE stock_move_id=%s", (consignment_location.id, move.id))
                            
                        move.invalidate_recordset(['location_dest_id'])
                        move.move_line_ids.invalidate_recordset(['location_dest_id'])
                        
                        self.env['stock.quant']._update_available_quantity(move.product_id, old_location, -qty_to_consignment)
                        self.env['stock.quant']._update_available_quantity(move.product_id, consignment_location, qty_to_consignment)
                    else:
                        # Chia tách: giảm Move gốc, tạo Move mới cho KKG
                        old_location = move.location_dest_id
                        new_qty = move.product_uom_qty - qty_to_consignment
                        
                        # Fix #1 & #2: Giảm cả product_uom_qty VÀ quantity_done
                        self.env.cr.execute(
                            "UPDATE stock_move SET product_uom_qty=%s, quantity_done=%s WHERE id=%s",
                            (new_qty, new_qty, move.id)
                        )
                        move.invalidate_recordset(['product_uom_qty', 'quantity_done', 'location_dest_id'])
                        
                        # Giảm qty_done trên SML gốc
                        line = move.move_line_ids[0]
                        self.env.cr.execute("UPDATE stock_move_line SET qty_done=%s WHERE id=%s", (new_qty, line.id))
                        line.invalidate_recordset(['qty_done'])
                        
                        # Tạo Move mới cho KKG
                        new_move_vals = move.copy_data({
                            'product_uom_qty': qty_to_consignment,
                            'location_dest_id': consignment_location.id,
                        })[0]
                        new_move = self.env['stock.move'].sudo().create(new_move_vals)
                        self.env.cr.execute(
                            "UPDATE stock_move SET state='done', quantity_done=%s WHERE id=%s",
                            (qty_to_consignment, new_move.id)
                        )
                        
                        # Fix #4: Tạo SML mới và ép state=done bằng SQL
                        new_line_vals = line.copy_data({
                            'move_id': new_move.id,
                            'location_dest_id': consignment_location.id,
                            'qty_done': qty_to_consignment,
                        })[0]
                        new_line = self.env['stock.move.line'].sudo().create(new_line_vals)
                        self.env.cr.execute("UPDATE stock_move_line SET state='done' WHERE id=%s", (new_line.id,))
                        
                        # Fix #3: Chia tách SVL theo tỷ lệ số lượng
                        for svl in self.env['stock.valuation.layer'].sudo().search([
                            ('stock_move_id', '=', move.id),
                            ('product_id', '=', move.product_id.id),
                        ]):
                            original_svl_qty = svl.quantity
                            if original_svl_qty <= 0:
                                continue
                            unit_cost = svl.unit_cost
                            new_svl_qty = qty_to_consignment
                            new_svl_value = round(unit_cost * new_svl_qty)
                            remaining_svl_qty = original_svl_qty - new_svl_qty
                            remaining_svl_value = svl.value - new_svl_value
                            
                            # Giảm SVL gốc
                            svl.sudo().write({
                                'quantity': remaining_svl_qty,
                                'value': remaining_svl_value,
                            })
                            
                            # Tạo SVL mới cho Move KKG
                            new_svl_vals = {
                                'product_id': move.product_id.id,
                                'company_id': move.company_id.id,
                                'stock_move_id': new_move.id,
                                'quantity': new_svl_qty,
                                'value': new_svl_value,
                                'unit_cost': unit_cost,
                                'remaining_qty': 0.0,
                                'remaining_value': 0.0,
                                'description': '%s - %s (KKG split)' % (production.name, move.product_id.display_name),
                            }
                            if 'location_dest_id' in self.env['stock.valuation.layer']._fields:
                                new_svl_vals['location_dest_id'] = consignment_location.id
                            self.env['stock.valuation.layer'].sudo().create(new_svl_vals)
                        
                        # Fix #1: Dùng old_location (đã lưu TRƯỚC khi invalidate) để trừ quant đúng kho
                        self.env['stock.quant']._update_available_quantity(move.product_id, old_location, -qty_to_consignment)
                        self.env['stock.quant']._update_available_quantity(move.product_id, consignment_location, qty_to_consignment)
                        
        return {'type': 'ir.actions.act_window_close'}

