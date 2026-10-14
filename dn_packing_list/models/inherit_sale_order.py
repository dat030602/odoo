from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError

class PackingListInheritSale(models.Model):
    _inherit = 'sale.order'

    customer_po_number = fields.Char(string="Customer PO Number")
    packing_list_id = fields.Many2one('packing.list', string='Packing List')

    so__y_count = fields.Integer(string="Account Move count", compute='_compute_pkl_count')
    
    # @api.depends('packing_list_ids')
    def _compute_pkl_count(self):
        for so in self:
            so.so__y_count = self.env['packing.list'].search_count([
                ('orders', '=', so.id),
                ('parent_packing_list_id', '=', False),
            ])

    def sale_order__packing_list(self):
        action = self.env['ir.actions.act_window']._for_xml_id('dn_packing_list.packing_list_action')
        action['domain'] = [
            ('orders', '=', self.id),
            ('parent_packing_list_id', '=', False),
        ]
        return action

    def _get_packable_product_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda line: not line.display_type)

    def add_to_pl(self):
        if self:
            if not self.partner_id:
                raise ValidationError(_("You must select a customer first"))
            product_lines = self._get_packable_product_lines()
            if not product_lines or all(
                line.packable_remaining_qty <= 0 for line in product_lines
            ):
                raise UserError(_(
                    "All items in this Sales Order are already packed. "
                    "Cannot create a new packing list."
                ))
            action ={
                'view_type':'form',
                'view_mode': 'form',
                'res_model' : 'add.to.packing.list.wizard',
                'view_id': self.env.ref('dn_packing_list.add_to_packing_list_wizard_form_view').id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_partner_id': self.partner_id.id,
                    'default_order_ids': self.ids,
                }
            }
            return action

    def _prepare_invoice(self):
        res = super(PackingListInheritSale,self)._prepare_invoice()
        packing_list = self.env.context.get('default_x_packing_list_id',False)
        if packing_list:
            res['packing_list_id'] = packing_list
        return res
    
    def _get_invoiceable_lines(self,final):
        res = super(PackingListInheritSale,self)._get_invoiceable_lines(final)
        context = self.env.context
        packing_list = context.get('default_x_packing_list_id',[])
        if packing_list:
            result = res & self.env['packing.list'].browse(packing_list).line_ids.order_line_id
            if context.get('x_invoice_service',False):
                result += res.filtered(lambda x: x.product_id.type == 'service' and not x.is_downpayment)
            if context.get('x_deduct_downpayments',False):
                result += res.filtered(lambda x: x.is_downpayment)
            return result
        return res

class PackingListInheritSaleLine(models.Model):
    _inherit = 'sale.order.line'

    packing_list_line_ids = fields.One2many(
        'packing.list.line',
        'order_line_id',
        string='Packing List Lines',
    )
    returned_packable_qty = fields.Float(
        string='Returned Packable Qty',
        compute='_compute_packable_remaining_qty',
        store=True,
        digits='Product Unit of Measure',
    )
    packable_remaining_qty = fields.Float(
        string='Remaining Packable Qty',
        compute='_compute_packable_remaining_qty',
        store=True,
        digits='Product Unit of Measure',
    )

    @api.model
    def _get_quota_counting_pl_line_domain(self, order_line_ids=None):
        """Domain for PL lines that consume SO line packable quota."""
        domain = [
            ('display_type', '=', False),
            ('packing_list_id.parent_packing_list_id', '=', False),
            '|',
            ('packing_list_id.stage_id', '=', False),
            ('packing_list_id.stage_id.is_closed', '=', False),
        ]
        if order_line_ids:
            domain.append(('order_line_id', 'in', order_line_ids))
        return domain

    def _get_packed_qty_on_active_parent_pls(self):
        """Sum quantity allocated on active (non-cancelled) parent packing lists."""
        self.ensure_one()
        pl_lines = self.packing_list_line_ids.filtered(
            lambda line: (
                not line.display_type
                and line.packing_list_id
                and not line.packing_list_id.parent_packing_list_id
                and (
                    not line.packing_list_id.stage_id
                    or not line.packing_list_id.stage_id.is_closed
                )
            )
        )
        return sum(pl_lines.mapped('quantity'))

    def _get_returned_packable_qty(self):
        """Sum done return moves (to_refund) credited back to packable quota."""
        self.ensure_one()
        _, incoming_moves = self._get_outgoing_incoming_moves()
        returned_qty = 0.0
        for move in incoming_moves.filtered(lambda m: m.state == 'done'):
            returned_qty += move.product_uom._compute_quantity(
                move.quantity,
                self.product_uom_id,
                rounding_method='HALF-UP',
            )
        return returned_qty

    def _format_sol_quantity(self, qty):
        self.ensure_one()
        uom_name = self.product_uom_id.display_name if self.product_uom_id else ''
        qty_label = f"{qty:g}"
        return f"{qty_label} {uom_name}".strip()

    @api.depends(
        'product_uom_qty',
        'display_type',
        'packing_list_line_ids.quantity',
        'packing_list_line_ids.display_type',
        'packing_list_line_ids.packing_list_id.parent_packing_list_id',
        'packing_list_line_ids.packing_list_id.stage_id.is_closed',
        'move_ids.state',
        'move_ids.quantity',
        'move_ids.to_refund',
    )
    def _compute_packable_remaining_qty(self):
        product_lines = self.filtered(lambda line: not line.display_type)
        (self - product_lines).packable_remaining_qty = 0.0
        (self - product_lines).returned_packable_qty = 0.0
        if not product_lines:
            return

        packed_by_order_line = defaultdict(float)
        pl_lines = self.env['packing.list.line'].search(
            self._get_quota_counting_pl_line_domain(product_lines.ids)
        )
        for pl_line in pl_lines:
            packed_by_order_line[pl_line.order_line_id.id] += pl_line.quantity or 0.0

        for line in product_lines:
            packed_qty = packed_by_order_line.get(line.id, 0.0)
            returned_qty = line._get_returned_packable_qty()
            line.returned_packable_qty = returned_qty
            line.packable_remaining_qty = (
                (line.product_uom_qty or 0.0) - packed_qty + returned_qty
            )

    @api.constrains('packable_remaining_qty')
    def _check_packable_remaining_qty(self):
        for line in self.filtered(lambda sol: not sol.display_type):
            if line.packable_remaining_qty < 0:
                ordered_qty = line.product_uom_qty or 0.0
                packed_qty = line._get_packed_qty_on_active_parent_pls()
                returned_qty = line.returned_packable_qty
                remaining_qty = line.packable_remaining_qty
                exceeded_qty = abs(remaining_qty)
                raise ValidationError(_(
                    "Packing quantity exceeds the ordered quantity for "
                    "%(product)s on %(order)s.\n"
                    "Ordered Qty: %(ordered_qty)s\n"
                    "Allocated on Parent PLs: %(packed_qty)s\n"
                    "Returned Qty: %(returned_qty)s\n"
                    "Remaining Packable Qty: %(remaining_qty)s\n"
                    "Exceeded by: %(exceeded_qty)s",
                    product=line.product_id.display_name,
                    order=line.order_id.name,
                    ordered_qty=line._format_sol_quantity(ordered_qty),
                    packed_qty=line._format_sol_quantity(packed_qty),
                    returned_qty=line._format_sol_quantity(returned_qty),
                    remaining_qty=line._format_sol_quantity(remaining_qty),
                    exceeded_qty=line._format_sol_quantity(exceeded_qty),
                ))

    def _prepare_invoice_line(self, **optional_values):
        res = super(PackingListInheritSaleLine,self)._prepare_invoice_line(**optional_values)
        packing_list = self.env.context.get('default_x_packing_list_id',[])
        if packing_list and not self.is_downpayment and not self.product_id.type == 'service':
            pl_lines = self.env['packing.list'].browse(packing_list).line_ids.filtered(lambda x: self == x.order_line_id)
            if pl_lines:
                res.update({
                  'quantity': sum(pl_lines.mapped('quantity')),
                  'price_unit': pl_lines[0].unit_price,
                })
        return res