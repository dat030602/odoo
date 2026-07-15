from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transport_ticket_ids = fields.One2many('transport.ticket', 'picking_id', string='Phiếu vận chuyển')

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        self.action_generate_transport_cost()
        return res

    def action_generate_transport_cost(self):
        # Filter only pickings that have a purchase order to avoid running logic for Sales/Internal transfers
        po_pickings = self.filtered(lambda p: p.purchase_id or (hasattr(p, 'purchase_order_id') and p.purchase_order_id))
        if not po_pickings:
            return
            
        # N+1 Optimization: Pre-fetch existing tickets for all pickings in one query. Must use sudo() to prevent Access Error for Inventory/Sales users
        existing_ticket_picking_ids = self.env['transport.ticket'].sudo().search([('picking_id', 'in', po_pickings.ids)]).mapped('picking_id.id')
        
        # Loop through picking to generate transport.ticket
        for picking in po_pickings:
            if picking.state != 'done':
                continue
                
            po = picking.purchase_id or (hasattr(picking, 'purchase_order_id') and picking.purchase_order_id)
            if not po:
                continue
                
            # Check if transport configurations exist on PO
            if not po.unload_container_id or not po.partner_unload_container_id:
                continue
                
            # Check if ticket already exists (using pre-fetched data)
            if picking.id in existing_ticket_picking_ids:
                continue
                
            # Calculate quantity and price unit
            is_truck = False
            if hasattr(po, 'transportation_id') and po.transportation_id:
                if po.transportation_id.name == 'Thuê ngoài theo Xe - Tấn':
                    is_truck = True
                    
            if is_truck and picking.picking_type_code != 'incoming':
                # For truck, we only create ticket for incoming shipments to avoid duplicates on internal transfers
                continue
                    
            quantity = 0.0
            price_unit = po.unload_container_id.standard_price
            unload_service_product = po.unload_container_id
            
            if is_truck:
                # Sum quantity_done of moves in this picking
                quantity = sum(picking.move_ids.filtered(lambda m: m.state == 'done').mapped('quantity_done'))
            else:
                # Find matching container lines on PO using python filter because picking_id and state are non-stored compute fields
                containers = po.stock_input_ids.filtered(
                    lambda c: c.picking_id.id == picking.id and c.state == 'done'
                )
                if containers:
                    quantity = float(len(containers))
                    # Take the first container's unload service if defined, otherwise fallback to PO's
                    first_container_service = containers[0].unload_container_id
                    if first_container_service:
                        unload_service_product = first_container_service
                        price_unit = first_container_service.standard_price
                else:
                    # Fallback to 1 if no container line matches but it is defined as container cước
                    quantity = 1.0
                    
            if quantity > 0:
                services = [unload_service_product]
                    
                for service in services:
                    service_sudo = service.sudo()
                    service_price_unit = service_sudo.standard_price
                    amount_total = quantity * service_price_unit
                    lc_id = False
                    
                    try:
                        with self.env.cr.savepoint():
                            # Fetch account for landed cost line
                            account_3351 = self.env['account.account'].sudo().search([
                                ('code', '=', '3351'), 
                                ('company_id', '=', picking.company_id.id)
                            ], limit=1)
                            
                            if account_3351:
                                account_id = account_3351.id
                            else:
                                account_id = service_sudo.property_account_expense_id.id or service_sudo.categ_id.property_account_expense_categ_id.id
                            
                            # Create Landed Cost with explicit Multi-Company Safety
                            landed_cost_vals = {
                                'company_id': picking.company_id.id,
                                'picking_ids': [(6, 0, [picking.id])],
                                'cost_lines': [(0, 0, {
                                    'product_id': service.id,
                                    'name': service.name or f"Cước {picking.name}",
                                    'account_id': account_id,
                                    'split_method': service.split_method_landed_cost or 'equal',
                                    'price_unit': amount_total, # Landed Cost price_unit is the TOTAL cost to allocate
                                })]
                            }
                            # MUST use sudo() because normal Warehouse workers do not have access to create Landed Costs or trigger Valuation
                            landed_cost = self.env['stock.landed.cost'].sudo().create(landed_cost_vals)
                            landed_cost.compute_landed_cost()
                            landed_cost.button_validate()
                            
                            # Cập nhật Đối tác (Partner) và Nhãn (Note) vào Bút toán định giá (Journal Entry)
                            if landed_cost.account_move_id:
                                move = landed_cost.account_move_id.sudo()
                                vals_to_update = {}
                                
                                partner_id = po.partner_unload_container_id.id if po.partner_unload_container_id else po.partner_id.id
                                if partner_id:
                                    vals_to_update['partner_id'] = partner_id
                                    
                                # Lấy note giống như bên Hạ cảng
                                stock_inputs = po.stock_input_ids.filtered(lambda l: l.picking_id.id == picking.id and l.state == 'done')
                                if stock_inputs:
                                    note = po._get_note_invoice(stock_inputs)
                                    if note:
                                        vals_to_update['note'] = note
                                        
                                if vals_to_update:
                                    move.write(vals_to_update)
                                    
                                line_vals_to_update = {}
                                if partner_id:
                                    line_vals_to_update['partner_id'] = partner_id
                                if stock_inputs and note:
                                    line_vals_to_update['name'] = note
                                    
                                if line_vals_to_update:
                                    move.line_ids.with_context(check_move_validity=False).write(line_vals_to_update)
                            
                            lc_id = landed_cost.id
                            _logger.info("Successfully created and validated Landed Cost %s for Picking %s", landed_cost.name, picking.name)
                    except Exception as e:
                        _logger.error("Failed to create/validate Landed Cost for picking %s: %s", picking.name, str(e))
                    
                    self.env['transport.ticket'].sudo().create({
                        'purchase_id': po.id,
                        'picking_id': picking.id,
                        'partner_id': po.partner_unload_container_id.id,
                        'unload_container_id': service.id,
                        'quantity': quantity,
                        'price_unit': service_price_unit,
                        'state': 'draft',
                        'landed_cost_id': lc_id,
                    })
                    _logger.info("Successfully created Transport Ticket for Picking %s (Service: %s)", picking.name, service.name)
