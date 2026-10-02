from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class InventoryCommitmentReport(models.Model):
    _name = 'inventory.commitment.report'
    _description = 'Inventory Commitment Report'
    _auto = False
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    move_id = fields.Many2one('stock.move', readonly=True)
    picking_id = fields.Many2one('stock.picking', readonly=True)
    sale_order_id = fields.Many2one('sale.order', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    demand_qty = fields.Float('Demand', readonly=True)
    reserved_qty = fields.Float('Reserved', readonly=True)
    commit_date = fields.Datetime('Commit Date', readonly=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'Urgent')], readonly=True)
    state = fields.Selection([
        ('draft', 'New'), ('cancel', 'Cancelled'), ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'), ('partially_available', 'Partially Available'),
        ('assigned', 'Available'), ('done', 'Done')
    ], readonly=True)
    
    # We will implement unreserve button directly here
    def action_release_reservation(self):
        moves = self.mapped('move_id')
        moves = moves.filtered(lambda m: m.state in ('partially_available', 'assigned'))
        if not moves:
            return True
        moves._do_unreserve()
        for m in moves:
            if m.picking_id:
                m.picking_id.message_post(body=_("Reservation released from Commitment Dashboard by %s") % self.env.user.name)
        return True

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    sm.id AS id,
                    sm.id AS move_id,
                    sm.product_id,
                    spt.warehouse_id,
                    sm.company_id,
                    sm.picking_id,
                    sol.order_id AS sale_order_id,
                    sp.partner_id,
                    sm.product_uom_qty AS demand_qty,
                    COALESCE((SELECT SUM(sml.quantity) FROM stock_move_line sml WHERE sml.move_id = sm.id), 0) AS reserved_qty,
                    COALESCE(so.commitment_date, sm.date) AS commit_date,
                    sp.priority,
                    sm.state
                FROM stock_move sm
                JOIN stock_picking sp ON sp.id = sm.picking_id
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                LEFT JOIN sale_order_line sol ON sol.id = sm.sale_line_id
                LEFT JOIN sale_order so ON so.id = sol.order_id
                WHERE sm.state IN ('confirmed','partially_available','assigned','waiting')
                AND spt.code = 'outgoing'
            )
        """ % self._table)

class InventoryCommitmentIncomingReport(models.Model):
    _name = 'inventory.commitment.incoming.report'
    _description = 'Inventory Commitment Incoming Report'
    _auto = False

    product_id = fields.Many2one('product.product', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    incoming_qty = fields.Float('Incoming', readonly=True)
    expected_date = fields.Datetime('Expected Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    pol.id AS id,
                    pol.product_id,
                    spt.warehouse_id,
                    po.id AS purchase_order_id,
                    po.partner_id,
                    (pol.product_qty - pol.qty_received) AS incoming_qty,
                    COALESCE(sp.scheduled_date, pol.date_planned) AS expected_date
                FROM purchase_order_line pol
                JOIN purchase_order po ON po.id = pol.order_id
                JOIN stock_picking_type spt ON spt.id = po.picking_type_id
                LEFT JOIN stock_move sm ON sm.purchase_line_id = pol.id
                LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
                WHERE po.state IN ('purchase', 'done')
                AND (pol.product_qty - pol.qty_received) > 0
                AND (sm.state NOT IN ('done', 'cancel') OR sm.id IS NULL)
            )
        """ % self._table)
