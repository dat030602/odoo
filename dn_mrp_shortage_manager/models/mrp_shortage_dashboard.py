from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict

class MrpShortageDashboard(models.TransientModel):
    _name = 'mrp.shortage.dashboard'
    _description = 'MRP Shortage Dashboard'

    warehouse_id = fields.Many2one('stock.warehouse')
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    include_forecast_receipts = fields.Boolean(default=True)
    line_ids = fields.One2many('mrp.shortage.line', 'dashboard_id')

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        
        domain = [('state', 'in', ('confirmed', 'progress', 'to_close'))]
        if self.warehouse_id:
            domain.append(('picking_type_id.warehouse_id', '=', self.warehouse_id.id))
        if self.date_from:
            domain.append(('date_start', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_start', '<=', self.date_to))
            
        mos = self.env['mrp.production'].search(domain)
        moves = mos.mapped('move_raw_ids').filtered(lambda m: m.state not in ('done', 'cancel'))
        
        shortages = defaultdict(lambda: {'demand': 0.0, 'reserved': 0.0, 'mos': self.env['mrp.production']})
        
        for move in moves:
            shortages[move.product_id]['demand'] += move.product_uom_qty
            shortages[move.product_id]['reserved'] += move.quantity
            shortages[move.product_id]['mos'] |= move.raw_material_production_id
            
        lines = []
        for product, data in shortages.items():
            demand = data['demand']
            reserved = data['reserved']
            if reserved < demand:
                missing = demand - reserved
                # Check free qty
                free_qty = product.with_context(warehouse_id=self.warehouse_id.id if self.warehouse_id else False).free_qty
                
                next_eta = False
                incoming_qty = 0.0
                covered_by_po = False
                
                if self.include_forecast_receipts:
                    pol = self.env['purchase.order.line'].search([
                        ('product_id', '=', product.id),
                        ('state', 'in', ('purchase', 'done')),
                    ], order='date_planned asc').filtered(lambda l: l.qty_received < l.product_qty)
                    
                    for line in pol:
                        incoming_qty += (line.product_qty - line.qty_received)
                        next_eta = line.date_planned
                        if incoming_qty >= missing:
                            covered_by_po = True
                            break
                            
                mo_dates = [d for d in data['mos'].mapped('date_start') if d]
                earliest_mo_date = min(mo_dates) if mo_dates else False
                
                lines.append((0, 0, {
                    'product_id': product.id,
                    'blocked_mo_count': len(data['mos']),
                    'production_ids': [(6, 0, data['mos'].ids)],
                    'required_qty': demand,
                    'available_qty': reserved + (free_qty if free_qty > 0 else 0),
                    'shortage_qty': missing,
                    'next_eta': next_eta,
                    'incoming_qty': incoming_qty,
                    'covered_by_po': covered_by_po,
                    'earliest_mo_date': earliest_mo_date,
                }))
                
        self.write({'line_ids': lines})
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.shortage.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current'
        }

class MrpShortageLine(models.TransientModel):
    _name = 'mrp.shortage.line'
    _description = 'MRP Shortage Line'

    dashboard_id = fields.Many2one('mrp.shortage.dashboard')
    product_id = fields.Many2one('product.product')
    blocked_mo_count = fields.Integer()
    production_ids = fields.Many2many('mrp.production')
    required_qty = fields.Float()
    available_qty = fields.Float()
    shortage_qty = fields.Float()
    next_eta = fields.Datetime()
    incoming_qty = fields.Float()
    covered_by_po = fields.Boolean()
    earliest_mo_date = fields.Datetime()

    def action_create_rfq(self):
        self.ensure_one()
        vendor = self.product_id.seller_ids[0].partner_id if self.product_id.seller_ids else False
        if not vendor:
            raise UserError(_("No vendor defined for product %s") % self.product_id.display_name)
            
        po = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product_id.id,
                'product_qty': self.shortage_qty,
                'price_unit': self.product_id.standard_price,
            })]
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current'
        }
