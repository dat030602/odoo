# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PackingListLine(models.Model):
    _name = 'packing.list.line'
    _description = 'Packing List Line'

    _LINES_LOCKED_WRITABLE_FIELDS = frozenset({'is_checked'})

    packing_list_id = fields.Many2one('packing.list', string='Packing List')
    lines_locked = fields.Boolean(related='packing_list_id.lines_locked')
    order_line_id = fields.Many2one('sale.order.line', string='Order Line')
    selectable_order_line_ids = fields.Many2many(
        'sale.order.line',
        compute='_compute_selectable_order_line_ids',
    )

    active = fields.Boolean(string='Active', related="packing_list_id.active")
    actual_freight_cost = fields.Float(string='Actual Freight Cost', related="packing_list_id.actual_freight_cost")
    all_shipped = fields.Boolean(string='All Shipped')
    barcode = fields.Char(string='Barcode')
    carton_end = fields.Char(string='Carton End')
    carton_net_weight = fields.Float(string='Carton Net Weight', digits="Stock Weight")
    carton_quantity = fields.Float(string='Carton Quantity', compute='_compute_carton_quantity', store=True, readonly=False, precompute=True)
    carton_start = fields.Char(string='Carton Start')
    code = fields.Char(string='Code')
    ctn_cbm = fields.Float(string='Ctn Cbm', compute='_compute_ctn_cbm', store=True)
    ctn_total_cbm = fields.Float(string='Carton Total Cbm', compute='_compute_ctn_total_cbm', store=True)
    ctn_type_id = fields.Many2one('carton.type', string='Ctn Type')
    ctn_weight = fields.Float(string='Ctn Weight', digits="Stock Weight", compute='_compute_ctn_type_fields', store=True, readonly=False, precompute=True)
    customer_number = fields.Char(string='Customer part number')
    delivery_slip = fields.Char(string='Delivery Slip', related="packing_list_id.code")
    description = fields.Char(string='Description')
    description_text = fields.Text(string='Description Test')
    distance_uom_id = fields.Many2one('uom.uom', string='Distance Uom')
    estimated_freight_cost = fields.Float(string='Estimated Freight Cost', related='packing_list_id.estimated_freight_cost')
    freight_invoiced_customer = fields.Float(string='Freight Invoiced to Customer', related="packing_list_id.freight_invoiced_customer")
    freight_prepaid = fields.Boolean(string='Freight Prepaid', related="packing_list_id.freight_prepaid")
    gross_weight = fields.Float(string='Gross Weight', digits="Stock Weight", compute='_compute_weights', store=True)
    height = fields.Float(string='Height', compute='_compute_ctn_type_fields', store=True, readonly=False, precompute=True)
    hs_code = fields.Char(string='HS code')
    inner_ctn_qty = fields.Float(string='Inner Carton Quantity')
    inventory_site = fields.Char(string='Inventory Site', related="packing_list_id.inventory_site")
    invoice_number = fields.Char(string='Invoice number')
    length = fields.Float(string='Length', compute='_compute_ctn_type_fields', store=True, readonly=False, precompute=True)
    name = fields.Char(string='Name', compute='_compute_order_line_fields', store=True, readonly=False, precompute=True)
    net_weight = fields.Float(string='Net Weight', digits="Stock Weight", compute='_compute_weights', store=True)
    notes = fields.Text(string='Notes')
    order_delivered_qty = fields.Float(string='Order Delivered Qty', related="order_line_id.qty_delivered")
    order_id = fields.Many2one('sale.order', string='Order', related="order_line_id.order_id")
    
    order_line_id_ref = fields.Integer(string='SO Line ID', related="order_line_id.id")
    order_qty = fields.Float(string='Order Qty')
    order_ref = fields.Char(string='Order Ref')
    order_remaining_qty = fields.Float(string='Remaining Qty of SO Line')
    
    pallet_cbm = fields.Float(string='Pallet CBM', compute='_compute_pallet_cbm', store=True)
    pallet_description = fields.Char(string='Pallets')
    pallet_gross_weight = fields.Float(string='Pallet Gross Weight', digits="Stock Weight")
    pallet_height = fields.Float(string='Pallet Height (cm)', digits="Volume", compute='_compute_type_pallet_fields', store=True, readonly=False, precompute=True)
    pallet_length = fields.Float(string='Pallet Length (cm)', digits="Volume", compute='_compute_type_pallet_fields', store=True, readonly=False, precompute=True)
    pallet_net_weight = fields.Float(string='Pallet Weight', digits="Stock Weight", compute='_compute_type_pallet_fields', store=True, readonly=False, precompute=True)
    pallet_qty = fields.Float(string='Pallet Qty', digits="Product Unit of Measure")
    pallet_total_cbm = fields.Float(string='Pallet Total Cbm', compute='_compute_pallet_total_cbm', store=True)
    pallet_width = fields.Float(string='Pallet Width (cm)', digits="Volume", compute='_compute_type_pallet_fields', store=True, readonly=False, precompute=True)
    parent_line_id = fields.Many2one('packing.list.line', string='Parent Line')
    child_line_ids = fields.One2many(
        'packing.list.line',
        'parent_line_id',
        string='Split Child Lines',
    )
    is_split = fields.Boolean(
        string='Already Split',
        compute='_compute_is_split',
    )
    partner_id = fields.Many2one('res.partner', string='Partner', related="packing_list_id.customer")
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_order_line_fields', store=True, readonly=False, precompute=True)
    product_net_weight = fields.Float(string='Product Net Weight', digits="Stock Weight", compute='_compute_order_line_fields', store=True, readonly=False, precompute=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Tmpl', related="product_id.product_tmpl_id")
    qty_per_carton = fields.Float(string='Qty Per Carton', compute='_compute_ctn_type_fields', store=True, readonly=False, precompute=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    sequence = fields.Integer(string='Sequence')
    shipped_quantity = fields.Float(string='Shipped Quantity', digits='Product Unit of Measure')
    shipping_marks = fields.Text(string='Shipping Marks')
    ship_status = fields.Char(string='Ship Status', related="packing_list_id.ship_status")
    size = fields.Char(string='Size')
    vendor_pl = fields.Char(string='Vendor PL', related="packing_list_id.vendor_pl")
    target_carton_weight = fields.Float(string='Target Carton Weight', digits="Stock Weight", compute='_compute_target_conversions', store=True)
    target_ctn_cbm = fields.Float(string='Target Ctn Cbm', compute='_compute_target_conversions', store=True)
    target_distance_uom_id = fields.Many2one('uom.uom', string='Target Distance')
    target_gross_weight = fields.Float(string='Target Gross Weight', digits="Stock Weight", compute='_compute_target_conversions', store=True)
    target_height = fields.Float(string='Target Height', compute='_compute_target_conversions', store=True)
    target_length = fields.Float(string='Target Length', compute='_compute_target_conversions', store=True)
    target_net_weight = fields.Float(string='Target Net Weight', digits="Stock Weight", compute='_compute_target_conversions', store=True)
    target_product_net_weight = fields.Float(string='Target Product Net Weight', digits="Stock Weight", compute='_compute_target_conversions', store=True)
    target_total_cbm = fields.Float(string='Target Total Cbm', compute='_compute_target_conversions', store=True)
    target_total_gross_weight = fields.Float(string='Target Total Gross Weight', digits="Stock Weight", compute='_compute_target_conversions', store=True)
    target_total_net_weight = fields.Float(string='Target Total Net Weight', digits="Stock Weight", compute='_compute_target_conversions', store=True)
    target_weight_uom_id = fields.Many2one('uom.uom', string='Target Weight Uom')
    
    target_width = fields.Float(string='Target Width', digits="Volume", compute='_compute_target_conversions', store=True)
    title = fields.Char(string='Title')
    total_amount = fields.Float(string='Total Amount', compute="_compute_total_amount", store=True)
    total_cbm = fields.Float(string='Total Cbm', compute='_compute_total_cbm', store=True)
    total_gross_weight = fields.Float(string='Total Gross Weight', digits="Stock Weight", compute='_compute_weights', store=True)
    total_net_weight = fields.Float(string='Total Net Weight', digits="Stock Weight", compute='_compute_weights', store=True)
    tracking = fields.Char(string='Tracking', related="packing_list_id.tracking")
    tradelink = fields.Char(string='Tradelink UDR', related="packing_list_id.tradelink_udr")
    type_pallet_id = fields.Many2one('carton.type', string='Type Pallet')
    packing_list_ctn_type = fields.Char(string='Packing List CTN Type')
    unit_price = fields.Float(string='Unit Price', digits='Product Price', compute='_compute_order_line_fields', store=True, readonly=False, precompute=True)
    vendor_po_no = fields.Char(string='Vendor PO No', related="packing_list_id.vendor_po_no")
    weight_uom_id = fields.Many2one('uom.uom', string='Weight Uom')
    width = fields.Float(string='Width', compute='_compute_ctn_type_fields', store=True, readonly=False, precompute=True)
    
    display_type = fields.Selection(
        string='Display Type',
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False,
    )
    is_checked = fields.Boolean(string='Check Line')

    @api.depends(
        'packing_list_id.orders',
        'packing_list_id.parent_packing_list_id',
        'order_line_id',
        'order_line_id.packable_remaining_qty',
    )
    def _compute_selectable_order_line_ids(self):
        sale_order_line_model = self.env['sale.order.line']
        for line in self:
            packing_list = line.packing_list_id
            if not packing_list or not packing_list.orders:
                line.selectable_order_line_ids = sale_order_line_model.browse()
                continue

            base_domain = [
                ('order_id', 'in', packing_list.orders.ids),
                ('display_type', '=', False),
            ]
            if packing_list.parent_packing_list_id:
                line.selectable_order_line_ids = sale_order_line_model.search(base_domain)
                continue

            line.selectable_order_line_ids = sale_order_line_model.search(
                base_domain + [
                    '|',
                    ('packable_remaining_qty', '>', 0),
                    ('id', '=', line.order_line_id.id),
                ]
            )

    @api.depends('child_line_ids')
    def _compute_is_split(self):
        for line in self:
            line.is_split = bool(line.child_line_ids)

    @api.depends('unit_price', 'quantity')
    def _compute_total_amount(self):
        for record in self:
            record["total_amount"] = (record.unit_price or 0.0) * (record.quantity or 0.0)

    def _raise_if_lines_locked(self, operation):
        if self.env.context.get('skip_lines_lock'):
            return
        if self.filtered(lambda line: line.packing_list_id.parent_packing_list_id):
            raise ValidationError(_(
                "Child packing list lines are read-only and cannot be %(operation)s.",
                operation=operation,
            ))
        locked_lines = self.filtered(lambda line: line.packing_list_id.lines_locked)
        if locked_lines:
            raise ValidationError(_(
                "Packing list lines are locked and cannot be %(operation)s.",
                operation=operation,
            ))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('skip_lines_lock'):
            for vals in vals_list:
                packing_list_id = vals.get('packing_list_id')
                if not packing_list_id:
                    continue
                packing_list = self.env['packing.list'].browse(packing_list_id)
                if packing_list.parent_packing_list_id or packing_list.lines_locked:
                    raise ValidationError(_(
                        "Packing list lines are locked and cannot be created."
                    ))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get('skip_lines_lock'):
            if self.filtered(lambda line: line.packing_list_id.parent_packing_list_id):
                self._raise_if_lines_locked('modified')
            locked_lines = self.filtered(
                lambda line: line.packing_list_id.lines_locked
            )
            if locked_lines and set(vals) - self._LINES_LOCKED_WRITABLE_FIELDS:
                self._raise_if_lines_locked('modified')
        if vals.get('is_checked'):
            split_lines = self.filtered('is_split')
            if split_lines:
                raise ValidationError(_("This line has already been split."))
        return super().write(vals)

    def unlink(self):
        self._raise_if_lines_locked('deleted')
        return super().unlink()

    def pll_duplicate(self):
        self._raise_if_lines_locked('duplicated')
        return self.copy()
    
    @api.depends('ctn_type_id')
    def _compute_ctn_type_fields(self):
        for line in self:
            if line.ctn_type_id:
                line.length = line.ctn_type_id.length
                line.width = line.ctn_type_id.width
                line.height = line.ctn_type_id.height
                line.ctn_weight = line.ctn_type_id.weight
                line.qty_per_carton = line.ctn_type_id.qty_per_carton
            else:
                line.length = line.length or 0.0
                line.width = line.width or 0.0
                line.height = line.height or 0.0
                line.ctn_weight = line.ctn_weight or 0.0
                line.qty_per_carton = line.qty_per_carton or 0.0

    @api.onchange('ctn_type_id')
    def _onchange_ctn_type_id(self):
        if self.ctn_type_id:
            self.length = self.ctn_type_id.length
            self.width = self.ctn_type_id.width
            self.height = self.ctn_type_id.height
            self.ctn_weight = self.ctn_type_id.weight
            self.qty_per_carton = self.ctn_type_id.qty_per_carton

    @api.depends('type_pallet_id')
    def _compute_type_pallet_fields(self):
        for line in self:
            if line.type_pallet_id:
                line.pallet_length = line.type_pallet_id.length
                line.pallet_width = line.type_pallet_id.width
                line.pallet_height = line.type_pallet_id.height
                line.pallet_net_weight = line.type_pallet_id.weight
            else:
                line.pallet_length = line.pallet_length or 0.0
                line.pallet_width = line.pallet_width or 0.0
                line.pallet_height = line.pallet_height or 0.0
                line.pallet_net_weight = line.pallet_net_weight or 0.0

    @api.onchange('type_pallet_id')
    def _onchange_type_pallet_id(self):
        if self.type_pallet_id:
            self.pallet_length = self.type_pallet_id.length
            self.pallet_width = self.type_pallet_id.width
            self.pallet_height = self.type_pallet_id.height
            self.pallet_net_weight = self.type_pallet_id.weight

    @api.depends('order_line_id')
    def _compute_order_line_fields(self):
        for line in self:
            if line.order_line_id:
                if not line.quantity:
                    line.quantity = line.order_line_id.packable_remaining_qty
                line.unit_price = line.order_line_id.price_unit
                line.name = line.order_line_id.name
                line.product_id = line.order_line_id.product_id
                line.product_net_weight = line.order_line_id.product_id.weight
            else:
                line.unit_price = line.unit_price or 0.0
                line.product_net_weight = line.product_net_weight or 0.0

    @api.onchange('order_line_id')
    def _onchange_order_line_id(self):
        if self.order_line_id:
            self.quantity = self.order_line_id.packable_remaining_qty
            self.unit_price = self.order_line_id.price_unit
            self.name = self.order_line_id.name
            self.product_id = self.order_line_id.product_id
            if self.order_line_id.product_id:
                self.product_net_weight = self.order_line_id.product_id.weight

    @api.depends('quantity', 'qty_per_carton')
    def _compute_carton_quantity(self):
        for line in self:
            if line.qty_per_carton:
                line.carton_quantity = line.quantity / line.qty_per_carton
            elif not line.carton_quantity:
                line.carton_quantity = 0.0

    @api.onchange('quantity', 'qty_per_carton')
    def _onchange_carton_qty(self):
        if self.qty_per_carton:
            self.carton_quantity = self.quantity / self.qty_per_carton
        else:
            self.carton_quantity = 0.0

    @api.depends('length', 'width', 'height')
    def _compute_ctn_cbm(self):
        for line in self:
            line.ctn_cbm = (line.length * line.width * line.height) / 1000000.0

    @api.depends('ctn_cbm', 'carton_quantity')
    def _compute_ctn_total_cbm(self):
        for line in self:
            line.ctn_total_cbm = line.ctn_cbm * line.carton_quantity

    @api.depends('pallet_length', 'pallet_width', 'pallet_height')
    def _compute_pallet_cbm(self):
        for line in self:
            line.pallet_cbm = (line.pallet_length * line.pallet_width * line.pallet_height) / 1000000.0

    @api.depends('pallet_cbm', 'pallet_qty')
    def _compute_pallet_total_cbm(self):
        for line in self:
            line.pallet_total_cbm = line.pallet_cbm * line.pallet_qty

    @api.depends('pallet_total_cbm', 'ctn_total_cbm')
    def _compute_total_cbm(self):
        for line in self:
            line.total_cbm = line.pallet_total_cbm if line.pallet_total_cbm else line.ctn_total_cbm

    @api.depends('carton_quantity', 'ctn_weight', 'quantity', 'product_net_weight')
    def _compute_weights(self):
        for line in self:
            line.net_weight = line.quantity * line.product_net_weight
            line.total_net_weight = line.net_weight
            line.gross_weight = line.net_weight + (line.carton_quantity * line.ctn_weight)
            line.total_gross_weight = line.gross_weight

    @api.depends('target_distance_uom_id', 'target_weight_uom_id', 'distance_uom_id', 'weight_uom_id',
                 'length', 'width', 'height', 'ctn_weight', 'product_net_weight', 'net_weight', 'gross_weight',
                 'ctn_cbm', 'ctn_total_cbm')
    def _compute_target_conversions(self):
        for line in self:
            duom = line.distance_uom_id or self.env.ref('uom.product_uom_cm', raise_if_not_found=False)
            tduom = line.target_distance_uom_id or duom
            wuom = line.weight_uom_id or self.env.ref('uom.product_uom_kgm', raise_if_not_found=False)
            twuom = line.target_weight_uom_id or wuom
            
            if duom and tduom:
                line.target_length = duom._compute_quantity(line.length, tduom)
                line.target_width = duom._compute_quantity(line.width, tduom)
                line.target_height = duom._compute_quantity(line.height, tduom)
            else:
                line.target_length = line.length
                line.target_width = line.width
                line.target_height = line.height
                
            if wuom and twuom:
                line.target_product_net_weight = wuom._compute_quantity(line.product_net_weight, twuom)
                line.target_carton_weight = wuom._compute_quantity(line.ctn_weight, twuom)
                line.target_net_weight = wuom._compute_quantity(line.net_weight, twuom)
                line.target_total_net_weight = line.target_net_weight
                line.target_gross_weight = wuom._compute_quantity(line.gross_weight, twuom)
                line.target_total_gross_weight = line.target_gross_weight
            else:
                line.target_product_net_weight = line.product_net_weight
                line.target_carton_weight = line.ctn_weight
                line.target_net_weight = line.net_weight
                line.target_total_net_weight = line.target_net_weight
                line.target_gross_weight = line.gross_weight
                line.target_total_gross_weight = line.target_gross_weight
                
            line.target_ctn_cbm = line.ctn_cbm
            line.target_total_cbm = line.ctn_total_cbm

    def reupdate_line_title(self):
        for rec in self:
            rec.title = rec.packing_list_id.title