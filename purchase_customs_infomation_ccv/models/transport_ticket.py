from odoo import models, fields, api
from odoo.exceptions import UserError

class TransportTicket(models.Model):
    _name = 'transport.ticket'
    _description = 'Transport Ticket'
    _order = 'id desc'

    name = fields.Char(string='Số phiếu cước', required=True, default='Mới', copy=False, readonly=True)
    purchase_id = fields.Many2one('purchase.order', string='Đơn mua hàng', readonly=True, index=True)
    picking_id = fields.Many2one('stock.picking', string='Phiếu kho', readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Nhà xe / Đối tác', readonly=True)
    unload_container_id = fields.Many2one('product.product', string='Cảng hạ / Dịch vụ', readonly=True)
    quantity = fields.Float(string='Số lượng', readonly=True, digits="Product Unit of Measure")
    price_unit = fields.Float(string='Đơn giá cước', readonly=True, digits="Product Price")
    amount_total = fields.Float(string='Thành tiền cước', compute='_compute_amount_total', store=True, digits="Product Price")
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('invoiced', 'Đã xuất hóa đơn')
    ], string='Trạng thái', compute='_compute_state', store=True, readonly=True, index=True)
    
    move_line_id = fields.Many2one('account.move.line', string='Dòng hóa đơn liên kết', readonly=True, ondelete='set null')
    move_id = fields.Many2one('account.move', string='Hóa đơn', related='move_line_id.move_id', store=True, index=True)
    landed_cost_id = fields.Many2one('stock.landed.cost', string='Phiếu phân bổ chi phí (Landed Cost)', readonly=True, ondelete='set null')
    
    billing_quantity = fields.Float(string='Số lượng quyết toán', digits="Product Unit of Measure")
    billing_price_unit = fields.Float(string='Đơn giá quyết toán', digits="Product Price")
    
    @api.depends('move_line_id')
    def _compute_state(self):
        for rec in self:
            if rec.move_line_id:
                rec.state = 'invoiced'
            else:
                rec.state = 'draft'

    @api.depends('quantity', 'price_unit')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.quantity * rec.price_unit

    def action_view_move(self):
        self.ensure_one()
        if self.move_id:
            return {
                'name': 'Hóa đơn',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.move_id.id,
            }
            
    def action_view_landed_cost(self):
        self.ensure_one()
        if self.landed_cost_id:
            return {
                'name': 'Landed Cost',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.landed.cost',
                'view_mode': 'form',
                'res_id': self.landed_cost_id.id,
            }

    @api.model
    def action_sync_transport_tickets(self):
        po_id = self._context.get('default_purchase_id')
        if not po_id:
            raise UserError('Không tìm thấy Đơn mua hàng để đồng bộ!')
            
        po = self.env['purchase.order'].browse(po_id)
        # Find all done pickings
        pickings = po.picking_ids.filtered(lambda p: p.state == 'done')
        
        # Call the logic on those pickings
        if pickings:
            pickings.action_generate_transport_cost()
            
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('transport.ticket') or 'Mới'
        return super(TransportTicket, self).create(vals_list)
