# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderStockInput(models.Model):
    _inherit = 'purchase.order.stock.input'
    
    weight_ccv = fields.Float(string='Cân CCV',
        digits="Product Unit of Measure",compute="_compute_picking_id")
    weight_port = fields.Float(string='Cân cảng',
        digits="Product Unit of Measure",compute="_compute_picking_id")
    
    @api.depends('container_number','seal_number')
    def _compute_picking_id(self):
        super()._compute_picking_id()
        for rec in self:
            if rec.picking_id:
                rec.weight_ccv = rec.picking_id.weight_ccv
                rec.weight_port = rec.picking_id.weight_port
            else:
                rec.weight_ccv = 0
                rec.weight_port = 0

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    has_unmatched_containers = fields.Boolean(
        string='Has Unmatched Containers',
        compute='_compute_has_unmatched_containers',
        store=False,
    )
    
    delivery_ids = fields.One2many(
        'stock.picking', 'purchase_order_id',
        string='Delivery Orders'
    )

    is_import = fields.Selection(
        [('in', 'Trong nước'), ('out', 'Ngoài nước')],
        string='Loại hàng',
        default='out',
        required=True,
    )
    
    def _compute_has_unmatched_containers(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            # Get all container numbers from stock_input_ids
            container_lines = order.stock_input_ids.filtered(lambda l: l.container_number)
            containers = set(container_lines.mapped('container_number'))
            # Get all container numbers from pickings linked to this PO
            picking_containers = set(
                StockPicking.search([
                    ('purchase_order_id', '=', order.id),
                    ('container_number', '!=', False),
                ]).mapped('container_number')
            )
            # If any container in stock_input_ids is not in pickings, set True
            order.has_unmatched_containers = bool(containers - picking_containers)

    def action_create_deliveries_by_container(self):
        """
        Create a delivery order (stock.picking) for each unique container_number
        in the related purchase.order.stock.input lines, using the selected picking_type_id from context or the order's default.
        """
        StockPicking = self.env['stock.picking']
        created_pickings = []
        for order in self:
            picking_type_id = self.env.context.get('picking_type_id') or order.picking_type_id.id
            container_lines = order.stock_input_ids.filtered(lambda l: l.container_number)
            containers = set(container_lines.filtered(lambda l: not l.is_sale).mapped('container_number'))
            # Get containers already having a picking for this PO
            picking_containers = set(
                StockPicking.search([
                    ('purchase_order_id', '=', order.id),
                    ('container_number', '!=', False),
                ]).mapped('container_number')
            )
            unmatched_containers = containers - picking_containers
            for container in unmatched_containers:
                lines = container_lines.filtered(lambda l: l.container_number == container)
                if not lines:
                    continue
                seal_number = lines[0].seal_number if lines and lines[0].seal_number else False
                stock_input_id = lines[0].id if lines else False
                if order.is_import == 'out':
                    note_template = self.env['ir.config_parameter'].sudo().get_param('purchase_to_delivery_ccv.delivery_note_template') or _(
                        "Import tons, {product_name}, {container_number}/{seal_number}, STK {custom_declaration_number}, date {custom_declaration_date} - {partner_name}"
                    )
                    note_content = note_template.format(
                        product_name = ", ".join(order.order_line.mapped('product_id.display_name')),
                        container_number = container,
                        seal_number = seal_number,
                        custom_declaration_number = order.custom_declaration_number or '',
                        custom_declaration_date = order.custom_declaration_date.strftime('%d/%m/%Y') if order.custom_declaration_date else '',
                        partner_name = order.partner_id.display_name,
                    )
                else:
                    note_template = "Nhập {uom_name}, {product_name}, {container_number}{seal_number} - {partner_name}"
                    note_content = note_template.format(
                        uom_name = ",".join(order.order_line.mapped('product_uom.name')),
                        product_name = ", ".join(order.order_line.mapped('product_id.display_name')),
                        container_number = container,
                        seal_number = f"/{seal_number}" if seal_number else '',
                        partner_name = order.partner_id.display_name,
                    )
                picking_vals = {
                    'picking_type_id': picking_type_id,
                    'partner_id': order.partner_id.id,
                    'origin': order.name,
                    'purchase_order_id': order.id,
                    'reason_output_input_stock': note_content
                }
                picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                loc_id = picking_type.default_location_src_id.id or order.partner_id.property_stock_supplier.id
                loc_dest_id = picking_type.default_location_dest_id.id or order.picking_type_id.default_location_dest_id.id
                picking_vals['location_id'] = loc_id
                picking_vals['location_dest_id'] = loc_dest_id
                picking_vals['container_number'] = container
                picking_vals['seal_number'] = seal_number
                picking_vals['stock_input_id'] = stock_input_id
                picking = StockPicking.create(picking_vals)
                # stock_input_line = lines[0]
                move_vals = []
                for po_line in order.order_line.filtered(lambda l:l.product_qty > 0):
                    qty = po_line.product_qty / (len(unmatched_containers) or 1)
                    move_vals.append({
                        'name': po_line.name,
                        'product_id': po_line.product_id.id,
                        'product_uom': po_line.product_uom.id,
                        'product_uom_qty': qty,
                        'picking_id': picking.id,
                        'location_id': loc_id,
                        'location_dest_id': loc_dest_id,
                        'purchase_line_id': po_line.id
                    })
                self.env['stock.move'].create(move_vals)
                created_pickings.append(picking)
        if not created_pickings:
            _logger.error('No deliveries created for PO(s): %s', ', '.join(self.mapped('name')))
            raise UserError(_('No deliveries created. Check container lines and products.'))
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['domain'] = [('id', 'in', [p.id for p in created_pickings])]
        return action
    
    def action_view_delivery_orders(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['domain'] = [('id', 'in', self.stock_input_ids.picking_id.ids)]
        action['context'] = {'default_purchase_order_id': self.id}
        return action

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        for order in self:
            # Lấy toàn bộ phiếu nhập kho liên quan
            pickings = order.stock_input_ids.picking_id | order.delivery_ids
            for picking in pickings:
                for move in picking.move_ids:
                    if not move.purchase_line_id:
                        # Tìm dòng PO tương ứng có cùng sản phẩm
                        po_line = order.order_line.filtered(lambda l: l.product_id == move.product_id)
                        if po_line:
                            move.write({'purchase_line_id': po_line[0].id})
        return res
