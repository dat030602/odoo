from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AllocationRun(models.Model):
    _name = 'allocation.run'
    _description = 'Allocation Run'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', default=lambda self: self.env['ir.sequence'].next_by_code('allocation.run'))
    rule_id = fields.Many2one('allocation.rule', string='Rule', required=True)
    product_ids = fields.Many2many('product.product', string='Products')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    mode = fields.Selection([
        ('simulate', 'Simulate'),
        ('apply', 'Apply')
    ], default='simulate', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('simulated', 'Simulated'),
        ('applied', 'Applied'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], default='draft')
    line_ids = fields.One2many('allocation.run.line', 'run_id', string='Lines')
    triggered_by = fields.Selection([
        ('manual', 'Manual'),
        ('cron', 'Cron')
    ], default='manual')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('allocation.run') or _('New')
        return super().create(vals_list)

    def _get_candidate_moves(self):
        domain = [
            ('state', 'in', ('confirmed', 'partially_available', 'assigned')),
            ('picking_type_id.code', '=', 'outgoing')
        ]
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.warehouse_id:
            domain.append(('location_id', 'child_of', self.warehouse_id.view_location_id.id))
        return self.env['stock.move'].search(domain)

    def _is_protected(self, move):
        if not self.rule_id.protect_started_picking:
            return False
        # If the picking has started (lines picked), protect it
        for line in move.picking_id.move_line_ids:
            if line.picked:
                return True
        return False

    def action_simulate(self):
        self.ensure_one()
        moves = self._get_candidate_moves()
        moves = moves.filtered(lambda m: not self._is_protected(m))
        
        self.line_ids.unlink()
        if not moves:
            self.write({'state': 'simulated'})
            return True

        lines = []
        for move in moves:
            score = self.rule_id._score(move)
            lines.append((0, 0, {
                'move_id': move.id,
                'picking_id': move.picking_id.id,
                'sale_order_id': move.sale_line_id.order_id.id if move.sale_line_id else False,
                'partner_id': move.picking_id.partner_id.id,
                'score': score,
                'demand_qty': move.product_uom_qty,
                'reserved_before': move.quantity,
                'reserved_after': move.quantity,
                'delta_qty': 0,
            }))
        self.write({'line_ids': lines, 'state': 'simulated'})
        return True

    def action_apply(self):
        self.ensure_one()
        moves = self._get_candidate_moves()
        moves = moves.filtered(lambda m: not self._is_protected(m))
        
        self.line_ids.unlink()
        if not moves:
            self.write({'state': 'applied'})
            return True

        # Lock moves
        self.env.cr.execute("SELECT id FROM stock_move WHERE id IN %s FOR UPDATE NOWAIT", (tuple(moves.ids),))
        
        snapshot = {m.id: m.quantity for m in moves}
        
        scored = sorted(moves, key=lambda m: self.rule_id._score(m), reverse=True)
        
        moves._do_unreserve()
        for move in scored:
            move._action_assign()
            
        # Write results
        lines = []
        rank = 1
        for move in scored:
            reserved_before = snapshot.get(move.id, 0.0)
            reserved_after = move.quantity
            lines.append((0, 0, {
                'move_id': move.id,
                'picking_id': move.picking_id.id,
                'sale_order_id': move.sale_line_id.order_id.id if move.sale_line_id else False,
                'partner_id': move.picking_id.partner_id.id,
                'score': self.rule_id._score(move),
                'rank': rank,
                'demand_qty': move.product_uom_qty,
                'reserved_before': reserved_before,
                'reserved_after': reserved_after,
                'delta_qty': reserved_after - reserved_before,
            }))
            rank += 1
            if reserved_before != reserved_after:
                move.picking_id.message_post(body=_("Reservation changed from %s to %s due to ATP re-allocation #%s") % (reserved_before, reserved_after, self.name))
                
        self.write({'line_ids': lines, 'state': 'applied'})
        return True

class AllocationRunLine(models.Model):
    _name = 'allocation.run.line'
    _description = 'Allocation Run Line'

    run_id = fields.Many2one('allocation.run', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move')
    picking_id = fields.Many2one('stock.picking')
    sale_order_id = fields.Many2one('sale.order')
    partner_id = fields.Many2one('res.partner')
    score = fields.Float('Score')
    rank = fields.Integer('Rank')
    demand_qty = fields.Float('Demand')
    reserved_before = fields.Float('Reserved Before')
    reserved_after = fields.Float('Reserved After')
    delta_qty = fields.Float('Delta')
