# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime

class PackingList(models.Model):
    _name = 'packing.list'
    _description = 'Packing List'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'sequence desc'
    _rec_name = "name"

    name = fields.Char(string="Name", compute='_compute_name', store=True, precompute=True, copy=False)
    title = fields.Char(string="Title", default="New Packing List")
    bl_number = fields.Char(string="BL Number")
    packing_instructions_filename = fields.Char(string="Filename for Packing Instructions", copy=False)
    packing_instructions = fields.Binary(string="Packing Instructions", copy=False)
    bl_file_filename = fields.Char(string="Filename for BL", copy=False)
    bl_file = fields.Binary(string="BL File", copy=False)
    order_number = fields.Char(string="Order Number")
    shipping_marks = fields.Char(string="Shipping Marks")
    vessel = fields.Char(string="Vessel")
    invoice_number = fields.Char(string="Invoice Number")
    container_number = fields.Char(string="Container number")
    goods_origin = fields.Char(string="Goods origin")
    container_information = fields.Char(string="Container information")

    stock_picking_ids = fields.One2many('stock.picking','packing_list_id', string='Related Stock Pickings')
    account_move_ids = fields.One2many('account.move','packing_list_id', string='Related Account Moves')
    packing_list_id__account_move_count = fields.Integer(string="Account Move count", compute='_compute_account_move_count')
    packing_list_id__stock_picking_count = fields.Integer(string="Stock Picking count", compute='_compute_packing_list_id')
    line_count = fields.Integer(string="Picking List Line count", compute='_compute_packing_list_line_count')
    packing_list_id__sales_order_count = fields.Integer(string="Sales Order count", compute='_compute_ref_so')
    sequence = fields.Integer(string="Sequence")

    total_cbm = fields.Float(string="Total Cbm", compute='_compute_totals', store=True)
    total_nw = fields.Float(string="Total Net Weight", compute='_compute_totals', store=True)
    total_gw = fields.Float(string="Total Gross Weight", compute='_compute_totals', store=True)
    number_cartons = fields.Float(string="Total Carton Quantity", digits="Product Unit of Measure", compute='_compute_totals', store=True)
    total_quantity = fields.Float(string="Total Quantity", digits="Product Unit of Measure", compute='_compute_totals', store=True)
    total_amount = fields.Float(string="Total Amount", digits="Product Price", compute='_compute_totals', store=True)
    total_pallet_quantity = fields.Float(string="Total Pallet Quantity", digits="Product Unit of Measure", compute='_compute_totals', store=True)

    invoice_date = fields.Date(string="Invoice Date",copy=False)
    date_arrival = fields.Date(string="Date Arrival",copy=False)
    date_loading = fields.Date(string="Date Loading",copy=False)
    date_departure = fields.Date(string="Date Departure",copy=False)
    
    priority = fields.Boolean(string="High Priority")
    active = fields.Boolean(string="Active", default=True)
    
    shipping_type = fields.Selection([
        ('ocean', 'Ocean'),
        ('air', 'Air'),
        ('land', 'Land')
    ], string="Shipping Type")
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')
    ], string="Kanban State")
    packing_list_type = fields.Selection([
        ('customer', 'Customer'),
        ('internal', 'Internal Material'),
        ('external', 'External Material')
    ],
        string="Packing List Type")
    
    payment_terms_id = fields.Many2one('account.payment.term', string="Payment Terms")
    incoterm = fields.Many2one('account.incoterms', string="Incoterm")
    responsible = fields.Many2one('res.users', string="Responsible")
    consignee = fields.Many2one('res.partner', string="Consignee")
    port_from_id = fields.Many2one('shipping.destination', string="Port From")
    port_to_id = fields.Many2one('shipping.destination', string="Port To")
    delivery_address = fields.Many2one('res.partner',string="Delivery Address")
    manufacturer_id = fields.Many2one('res.partner', string="Manufacturer")
    customer = fields.Many2one('res.partner', string="Customer")
    shipper = fields.Many2one('res.partner', string="Shipper")

    forwarder_id = fields.Many2one('res.partner',string="Forwarder")

    stage_lock = fields.Boolean(string="Stage Lock",default=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
    line_ids = fields.One2many('packing.list.line', 'packing_list_id', string="Lines")
    parent_packing_list_id = fields.Many2one(
        'packing.list',
        string="Parent Packing List",
        ondelete='set null',
        copy=False,
        index=True,
    )
    child_packing_list_ids = fields.One2many(
        'packing.list',
        'parent_packing_list_id',
        string="Child Packing Lists",
    )
    child_packing_list_count = fields.Integer(
        string="Child Packing List Count",
        compute='_compute_child_packing_list_count',
    )
    orders = fields.Many2many('sale.order', string="Orders")

    actual_freight_cost = fields.Float(string="Actual Freight Cost", digits="Product Price")
    freight_invoiced_customer = fields.Float(string="Freight Invoiced to Customer")
    freight_prepaid = fields.Boolean(string="Freight Prepaid")
    inventory_site = fields.Char(string="Inventory Site")
    vendor_pl = fields.Char(string="Vendor PL")
    vendor_po_no = fields.Char(string="Vendor PO No")
    tracking = fields.Char(string="Tracking")
    tradelink_udr = fields.Char(string="Tradelink UDR")
    ship_status = fields.Char(string="Ship Status")
    loading_ref = fields.Char(string="Loading Ref")
    ref = fields.Char(string="Ref", compute='_compute_ref_so')
    estimated_freight_cost = fields.Float(string='Estimated Freight Cost', digits="Product Price")
    declare  = fields.Boolean(string="Declare Y/N")
    local_charges  = fields.Boolean(string="Local Charges")
    mate_receipt  = fields.Boolean(string="Mate Receipt")
    notes = fields.Text(string="Notes")

    def _default_code_prefix(self):
        seq = self.env.ref('dn_packing_list.dn_sequence_packing_list_increase', raise_if_not_found=False)
        return seq.prefix if seq else 'PACK/'

    code_prefix = fields.Char(default=_default_code_prefix,store=True)

    stage_id = fields.Many2one(
        'packing.list.stage',
        string="Stage",
        default=lambda self: self.env['packing.list.stage'].search(
            [('active', '=', True), ('is_closed', '=', False)],
            limit=1,
            order="sequence asc",
        ),
        tracking=True,
        copy=False,
    )
    stage_id_lock = fields.Many2one('packing.list.stage', string="Stage lock", related="stage_id",copy=False)
    code = fields.Char(string="Code")

    next_stage_id = fields.Many2one('packing.list.stage', compute='_compute_stage_navigation')
    prev_stage_id = fields.Many2one('packing.list.stage', compute='_compute_stage_navigation')
    next_stage_name = fields.Char(compute='_compute_stage_navigation')
    can_move_forward = fields.Boolean(compute='_compute_stage_navigation')
    can_move_back = fields.Boolean(compute='_compute_stage_navigation')
    show_deliver_button = fields.Boolean(compute='_compute_stage_navigation')
    show_invoice_button = fields.Boolean(compute='_compute_stage_navigation')
    is_cancel_allowed = fields.Boolean(compute='_compute_stage_navigation')
    lines_locked = fields.Boolean(compute='_compute_lines_locked')

    @api.depends('stage_id', 'parent_packing_list_id')
    def _compute_lines_locked(self):
        delivered = self.env.ref(
            'dn_packing_list.dn_packing_list_stage__delivered',
            raise_if_not_found=False,
        )
        invoiced = self.env.ref(
            'dn_packing_list.dn_packing_list_stage__invoiced',
            raise_if_not_found=False,
        )
        locked_stage_ids = {stage.id for stage in (delivered, invoiced) if stage}
        for record in self:
            record.lines_locked = bool(
                not record.parent_packing_list_id
                and record.stage_id.id in locked_stage_ids
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['code'] = self.env['ir.sequence'].next_by_code('sequence_packing_list')
        return super(PackingList, self).create(vals_list)

    @api.depends('code', 'title')
    def _compute_name(self):
        for record in self:
            record.name = f"[{record.code}]{record.title}"

    @api.depends('orders')
    def _compute_ref_so(self):
        for record in self:
            res = record.orders.mapped("customer_po_number")
            record.packing_list_id__sales_order_count = self.env['sale.order'].search_count([('id', 'in', self.orders.ids)])
            record.ref = ",".join([str(r) for r in res])

    @api.depends('stock_picking_ids')
    def _compute_packing_list_id(self):
        for rec in self:
            rec.packing_list_id__stock_picking_count = self.env['stock.picking'].search_count([('packing_list_id', '=', rec.id)])

    @api.depends('account_move_ids')
    def _compute_account_move_count(self):
        for rec in self:
            rec.packing_list_id__account_move_count = self.env['account.move'].search_count([('packing_list_id', '=', rec.id)])

    @api.depends('line_ids')
    def _compute_packing_list_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.depends('child_packing_list_ids')
    def _compute_child_packing_list_count(self):
        for record in self:
            record.child_packing_list_count = len(record.child_packing_list_ids)

    def add_to_pl(self):
        if self:
            if not self.customer:
                raise ValidationError(_("You must select a customer first"))
            action ={
                'view_type':'form',
                'view_mode': 'form',
                'res_model' : 'add.to.packing.list.wizard',
                'view_id': self.env.ref('dn_packing_list.add_to_packing_list_wizard_form_view').id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_partner_id': self.customer.id,
                    'default_order_id': self.orders.ids,
                    'default_target_packing_list': self.id,
                }
            }
            # Call the action_update_pl() function after the action is returned
            self.action_update_pl()
            return action   
        
    def pl_display_so(self):
        return {
            'name': 'Sales Orders',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.orders.ids)],
        }

    def packing_list_id__stock_picking(self):
        return {
            'name': 'Deliveries',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'domain': [('packing_list_id', '=', self.id)],
        }

    def packing_list_id__account_move(self):
        return {
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('packing_list_id', '=', self.id)],
        }

    def action_view_lines(self):
        return {
            'name': 'Packing List Line',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'packing.list.line',
            'type': 'ir.actions.act_window',
            'domain': [('packing_list_id', '=', self.id)],
        }

    def action_view_child_packing_lists(self):
        self.ensure_one()
        return {
            'name': _('Child Packing Lists'),
            'type': 'ir.actions.act_window',
            'res_model': 'packing.list',
            'view_mode': 'list,form',
            'domain': [('parent_packing_list_id', '=', self.id)],
            'context': {'default_parent_packing_list_id': self.id},
        }

    def action_view_parent_packing_list(self):
        self.ensure_one()
        if not self.parent_packing_list_id:
            return False
        return {
            'name': _('Parent Packing List'),
            'type': 'ir.actions.act_window',
            'res_model': 'packing.list',
            'view_mode': 'form',
            'res_id': self.parent_packing_list_id.id,
        }
        
    def _get_navigable_stage_domain(self):
        return [('active', '=', True), ('is_closed', '=', False)]

    def _get_next_stage(self, current_stage):
        if not current_stage:
            return self.env['packing.list.stage']
        return self.env['packing.list.stage'].search(
            self._get_navigable_stage_domain() + [('sequence', '>', current_stage.sequence)],
            order='sequence asc',
            limit=1,
        )

    def _get_prev_stage(self, current_stage):
        if not current_stage:
            return self.env['packing.list.stage']
        return self.env['packing.list.stage'].search(
            self._get_navigable_stage_domain() + [('sequence', '<', current_stage.sequence)],
            order='sequence desc',
            limit=1,
        )

    def _get_pl_pickings(self):
        self.ensure_one()
        return self.env['stock.picking'].search([
            ('packing_list_id', '=', self.id),
            ('state', '!=', 'cancel'),
        ])

    def _all_deliveries_returned(self):
        self.ensure_one()
        pickings = self._get_pl_pickings()
        if not pickings:
            return True
        return all(picking.has_return_picking() for picking in pickings)

    def _has_active_invoice(self):
        self.ensure_one()
        return bool(self.env['account.move'].search([
            ('packing_list_id', '=', self.id),
            ('state', '!=', 'cancel'),
        ], limit=1))

    @api.depends(
        'stage_id',
        'stage_id.is_delivery',
        'stage_id.is_invoice',
        'stage_id.is_closed',
        'stage_id.is_loading',
        'stage_id.sequence',
        'stage_id.active',
        'parent_packing_list_id',
        'stock_picking_ids.state',
        'stock_picking_ids.return_ids',
        'stock_picking_ids.return_ids.state',
        'account_move_ids.state',
    )
    def _compute_stage_navigation(self):
        for record in self:
            next_stage = record._get_next_stage(record.stage_id)
            prev_stage = record._get_prev_stage(record.stage_id)
            show_deliver = bool(record.stage_id.is_delivery)
            show_invoice = bool(record.stage_id.is_invoice)

            record.next_stage_id = next_stage
            record.prev_stage_id = prev_stage
            record.next_stage_name = next_stage.name if next_stage else False
            record.show_deliver_button = show_deliver
            record.show_invoice_button = show_invoice
            record.can_move_forward = bool(next_stage) and not show_deliver and not show_invoice
            record.can_move_back = (
                bool(prev_stage)
                and not record.stage_id.is_closed
                and not record.parent_packing_list_id
                and record._all_deliveries_returned()
                and not record._has_active_invoice()
            )
            record.is_cancel_allowed = (
                not record.parent_packing_list_id
                and not record.stage_id.is_closed
                and not record.lines_locked
            )

    def move_back(self):
        for record in self:
            if record.parent_packing_list_id:
                raise ValidationError(_("Child packing lists cannot change stage."))
            if not record._all_deliveries_returned():
                raise ValidationError(_(
                    "All delivery orders must have a return before going back."
                ))
            if record._has_active_invoice():
                raise ValidationError(_(
                    "Cancel or delete the invoice before going back."
                ))
            prev_stage = record._get_prev_stage(record.stage_id)
            if prev_stage:
                record.stage_id = prev_stage

    def move_forward(self):
        for record in self:
            next_stage = record._get_next_stage(record.stage_id)
            if not next_stage:
                continue
            record.stage_id = next_stage
            if next_stage.is_loading:
                record.date_loading = datetime.date.today()

    def button_cancel(self):
        for record in self:
            if record.parent_packing_list_id:
                raise ValidationError(_("Child packing lists cannot be cancelled."))
            if record.stage_id.is_closed:
                raise ValidationError(_("This packing list is already cancelled."))
            if record.lines_locked:
                raise ValidationError(_(
                    "This packing list has already been delivered or invoiced. "
                    "Goods must be returned via a Return Picking before the packing list "
                    "can be cancelled."
                ))
            cancel = self.env['packing.list.stage'].search([('is_closed', '=', True)], limit=1)
            if not cancel:
                cancel = self.env.ref(
                    'dn_packing_list.dn_packing_list_stage__cancelled',
                    raise_if_not_found=False,
                )
            if not cancel:
                raise ValidationError(_("Don't have 'Cancelled' stage at the moment!"))
            record.stage_id = cancel.id

    def setName(self,sheet):
        others= sheet.env['packing.list'].search([
            ('code','=',sheet.name),
            ('id','!=',sheet.id)
        ],limit=1)
        v = {}
        if not sheet['code'] or (sheet['code'] == 'New') or (sheet['code'] == '') or len(others) > 0:
            v['code'] = self.env['ir.sequence'].sudo().next_by_code('sequence_packing_list')
        v['name'] = "[" + str(sheet.code) + "] "+  str(sheet.title or "")
        return v

    @api.depends('line_ids.quantity', 'line_ids.total_net_weight', 'line_ids.total_gross_weight',
                 'line_ids.carton_quantity', 'line_ids.total_cbm', 'line_ids.total_amount', 'line_ids.pallet_qty')
    def _compute_totals(self):
        for record in self:
            record.total_quantity = sum(record.line_ids.mapped('quantity'))
            record.total_nw = sum(record.line_ids.mapped('total_net_weight'))
            record.total_gw = sum(record.line_ids.mapped('total_gross_weight'))
            record.number_cartons = sum(record.line_ids.mapped('carton_quantity'))
            record.total_cbm = sum(record.line_ids.mapped('total_cbm'))
            record.total_amount = sum(record.line_ids.mapped('total_amount'))
            record.total_pallet_quantity = sum(record.line_ids.mapped('pallet_qty'))

    def action_update_pl(self):
        for sheet in self:
            vr = self.setName(sheet)
            if not sheet.payment_terms_id and sheet.customer.property_payment_term_id:
                vr["payment_terms_id"] = sheet.customer.property_payment_term_id.id
            sheet.write(vr)

    def action_deliver(self):
        for record in self:
            if not record.customer or not record.delivery_address or not record.company_id:
                raise ValidationError(_("Customer, Delivery Address and Company are required to deliver."))
            pickings = self.env['stock.picking']
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('company_id', '=', record.company_id.id)], limit=1)
            if not picking_type:
                raise ValidationError(_("No outgoing picking type found for the company."))
            
            # Create a dictionary to group lines by order (if needed) or just create one picking
            picking_vals = {
                'partner_id': record.delivery_address.id,
                'picking_type_id': picking_type.id,
                'origin': record.name,
                'company_id': record.company_id.id,
                'packing_list_id': record.id,
            }
            picking = self.env['stock.picking'].create(picking_vals)
            
            for line in record.line_ids:
                if not line.product_id:
                    continue
                self.env['stock.move'].create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': picking_type.default_location_src_id.id,
                    'location_dest_id': picking.partner_id.property_stock_customer.id,
                })
            
            picking.action_confirm()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            picking.button_validate()
            
            delivered_stage = self.env.ref('dn_packing_list.dn_packing_list_stage__delivered', raise_if_not_found=False)
            if delivered_stage:
                record.stage_id = delivered_stage.id

    def action_create_invoice(self):
        for record in self:
            if not record.customer or not record.company_id:
                raise ValidationError(_("Customer and Company are required to invoice."))
            
            journal = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', record.company_id.id)], limit=1)
            if not journal:
                raise ValidationError(_("No sales journal found for the company."))
            
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': record.customer.id,
                'journal_id': journal.id,
                'company_id': record.company_id.id,
                'invoice_origin': record.name,
                'packing_list_id': record.id,
                'invoice_line_ids': [],
            }
            
            for line in record.line_ids:
                if not line.product_id:
                    continue
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'price_unit': line.unit_price,
                    'product_uom_id': line.product_id.uom_id.id,
                }))
                
            invoice = self.env['account.move'].create(invoice_vals)
            
            invoiced_stage = self.env.ref('dn_packing_list.dn_packing_list_stage__invoiced', raise_if_not_found=False)
            if invoiced_stage:
                record.stage_id = invoiced_stage.id

    def action_update_pl_line_title(self):
        self.line_ids.reupdate_line_title()

    def _get_next_child_code(self):
        self.ensure_one()
        prefix = f"{self.code}-"
        max_suffix = 0
        for child in self.child_packing_list_ids:
            if child.code and child.code.startswith(prefix):
                suffix_str = child.code[len(prefix):]
                if suffix_str.isdigit() and len(suffix_str) == 3:
                    max_suffix = max(max_suffix, int(suffix_str))
        return f"{self.code}-{max_suffix + 1:03d}"

    def action_create_child_packing_list(self):
        self.ensure_one()
        if self.parent_packing_list_id:
            raise ValidationError(_("Child packing lists cannot be split further."))

        lines_checked = self.line_ids.filtered('is_checked')
        if not lines_checked:
            raise ValidationError(_("Please check at least one line"))

        already_split = lines_checked.filtered('is_split')
        if already_split:
            raise ValidationError(_("This line has already been split."))

        child_code = self._get_next_child_code()
        child = self.copy({
            'line_ids': False,
            'parent_packing_list_id': self.id,
            'orders': [(5, 0, 0)],
            'shipping_marks': False,
        })
        child.write({'code': child_code, 'title': child_code})

        for line in lines_checked:
            line.with_context(skip_lines_lock=True).copy({
                'packing_list_id': child.id,
                'parent_line_id': line.id,
                'is_checked': False,
            })
        lines_checked.write({'is_checked': False})

        order_ids = lines_checked.filtered('order_line_id').mapped('order_line_id.order_id').ids
        if order_ids:
            child.write({'orders': [(6, 0, order_ids)]})

        self.action_update_pl()
        child.action_update_pl()

        return {
            'name': _('Child Packing List'),
            'type': 'ir.actions.act_window',
            'res_model': 'packing.list',
            'view_mode': 'form',
            'res_id': child.id,
            'target': 'current',
        }