from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby

_logger = logging.getLogger(__name__)

class PurchaseOrderStockInput(models.Model):
    _name = 'purchase.order.stock.input'
    _description = 'Purchase Order Stock Input Line'
    _order = 'id desc'

    order_id = fields.Many2one('purchase.order', string='Purchase Order', required=True, ondelete='cascade', index=True)
    container_number = fields.Char(string='Container Number', help='Container number')
    seal_number = fields.Char(string='Seal Number', help='Seal number')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    location_dest_id = fields.Many2one('stock.location', string='Destination Location',compute="_compute_picking_id")
    product_uom_qty = fields.Float(string='Quantity', default=0.0, digits="Product Unit of Measure", compute="_compute_picking_id")
    carrier_tracking_ref = fields.Char(string='Tracking Reference')
    picking_id = fields.Many2one('stock.picking',string="Điều chuyển",compute="_compute_picking_id")
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', related='picking_id.sale_id')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('waiting', 'Chờ hoạt động khác'),
        ('confirmed', 'Chờ'),
        ('assigned', 'Sẵn sàng'),
        ('done', 'Hoàn tất'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', compute="_compute_picking_id")
    is_sale = fields.Boolean(string='Đơn bán cảng')
    unload_container_id = fields.Many2one('product.product', string="Cảng hạ")

    _sql_constraints = [
        ('container_order_unique',
         'unique(order_id, container_number)',
         'Container number must be unique per purchase order.')
    ]
    
    @api.onchange('is_sale')
    def _onchange_is_sale(self):
        for rec in self:
            if rec.is_sale:
                rec.picking_id.filtered(lambda l: l.state not in ('done','cancel') and l.stock_input_id is not False).action_cancel()
    
    @api.depends('container_number', 'seal_number')
    def _compute_picking_id(self):
        """
        Computes the picking, state, and destination location based on container and seal numbers.

        This method handles cases where the stock.picking's 'container_number' field
        may contain multiple, comma-separated container numbers.

        The logic is as follows:
        1. It searches for candidate pickings that contain the current record's container number.
        2. For each candidate, it splits the 'container_number' string into a list.
        3. It trims whitespace from each container number in the list for accurate matching.
        4. **Special Rule**: If the current record's container number is found at the
        second position (index 1) in the list, that picking is considered invalid and skipped.
        5. The first valid picking found is assigned to `rec.picking_id`.
        6. If no valid picking is found, the fields are set to their default values.
        """
        for rec in self:
            # Initialize fields with default values
            rec.picking_id = False
            rec.state = 'draft'
            rec.location_dest_id = False
            rec.product_uom_qty = 0.0

            picking = self.env['stock.picking'].search([
                ('container_number', 'like', rec.container_number),
                ('seal_number', 'like', rec.seal_number),
                ('state', '!=', 'cancel')
            ], limit=1)

            valid_picking = False
            picking_containers = [c.strip() for c in (picking.container_number or '').split(',')]
            if rec.container_number in picking_containers:
                index = picking_containers.index(rec.container_number)
                valid_picking = picking
                rec.product_uom_qty = sum(valid_picking.move_ids.mapped('quantity_done'))
                if index == 1:
                    rec.state = valid_picking.state
                    rec.location_dest_id = valid_picking.location_dest_id
                else:
                    rec.picking_id = valid_picking.id
                    rec.state = valid_picking.state
                    rec.location_dest_id = valid_picking.location_dest_id

    def _prepare_account_move_line(self):
        self.ensure_one()
        company_id = self.env.company
        currency = company_id.currency_id
        date = fields.Date.today()
        parent_product = self.env['product.product'].search([
            ('unload_container_ids', 'in', [self.unload_container_id.product_tmpl_id.id])
        ], limit=1)
        res = False
        if parent_product:
            res = {
                'display_type': 'product',
                'name': self.order_id._get_note_invoice(self),
                'product_id': parent_product.id,
                'product_uom_id': parent_product.uom_po_id.id,
                'quantity': 1,
                'price_unit': currency._convert(self.unload_container_id.standard_price, currency, company_id, date, round=False),
                'tax_ids': [(6, 0, self.unload_container_id.supplier_taxes_id.ids)],
            }
        return res

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    carrier_name = fields.Char(
        string='Carrier Name',
    )
    bl_number = fields.Char(
        string='B/L No',
        help='Bill of Lading Number'
    )
    vessel_name = fields.Char(
        string='Vessel Name',
    )
    voyage_number = fields.Char(
        string='Voyage No',
        help='Voyage Number'
    )
    arrival_date_estimated = fields.Date(
        string='Arrival Date',
    )
    port_storage_duration = fields.Integer(
        string='Port Storage Duration',
        default=0,
    )
    transfer_qty_total = fields.Float(
        string='Total Transfer Quantity',
        compute='_compute_transfer_qty',
        store=True,
    )
    custom_declaration_number = fields.Char(
        string='Custom Declaration Number',
    )
    custom_declaration_date = fields.Date(
        string='Custom Declaration Date',
    )
    customs_attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Customs Attachments',
    )
    stock_input_ids = fields.One2many(
        'purchase.order.stock.input',
        'order_id',
        string='Stock Input Info',
    )
    unload_container_id = fields.Many2one('product.product', string="Cảng hạ", domain="[('detailed_type','=','service')]")
    has_unload_container = fields.Boolean(compute="_compute_unload_container_id")
    inv_unload_container_ids = fields.Many2many(
        'account.move',
        'purchase_unload_invoice_rel',
        'purchase_id',
        'invoice_id',
        string="Chi phí Cảng hạ",
        domain="[('move_type', '=', 'in_invoice')]")
    inv_unload_container_count = fields.Integer(compute="_compute_inv_unload_container_count")
    partner_unload_container_id = fields.Many2one('res.partner', string="Bên Vận chuyển")

    @api.onchange('partner_id')
    def _onchange_partner_unload_container_id(self):
        for rec in self:
            rec.partner_unload_container_id = rec.partner_id

    @api.depends('inv_unload_container_ids')
    def _compute_inv_unload_container_count(self):
        for rec in self:
            rec.inv_unload_container_count = len(rec.inv_unload_container_ids)


    @api.onchange('unload_container_id')
    def _onchange_unload_container_id(self):
        for rec in self:
            rec.stock_input_ids.unload_container_id = rec.unload_container_id
    
    @api.depends('unload_container_id','stock_input_ids.unload_container_id')
    def _compute_unload_container_id(self):
        for rec in self:
            unload_container_id = rec.unload_container_id or rec.stock_input_ids.mapped('unload_container_id')
            rec.has_unload_container = True if unload_container_id else False

    @api.depends('stock_input_ids')
    def _compute_transfer_qty(self):
        """Compute total transfer quantity from stock input lines"""
        for record in self:
            record.transfer_qty_total = sum(record.stock_input_ids.mapped('product_uom_qty'))

    def write(self, vals):
        res = super().write(vals)
        if 'customs_attachment_ids' in vals:
            self._message_attachments()
        return res

    def _message_attachments(self):
        if not self.customs_attachment_ids:
            return
            
        attachment_names = ", ".join(self.customs_attachment_ids.mapped('name'))
        self.message_post(
            body=f"Shipping documents uploaded: {attachment_names}",
            message_type="notification",
            subtype_xmlid="mail.mt_note",
            attachment_ids=self.customs_attachment_ids.ids
        )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for rec in res:
            rec._check_transportation_rules()
        return res

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec._check_transportation_rules()
        return res

    def _check_transportation_rules(self):
        if hasattr(self, 'transportation_id') and self.transportation_id:
            allowed_modes = ['CCV vận chuyển', 'Thuê ngoài theo Cont', 'Thuê ngoài theo Xe - Tấn', 'Bao vận chuyển', 'Khác']
            if self.transportation_id.name not in allowed_modes:
                raise ValidationError("Phương thức vận chuyển phải thuộc 1 trong 5 loại sau: " + ", ".join(allowed_modes))
            
            if self.transportation_id.name in ['Thuê ngoài theo Cont', 'Thuê ngoài theo Xe - Tấn']:
                if not self.partner_unload_container_id or not self.unload_container_id:
                    raise ValidationError("Khi chọn Phương thức vận chuyển là 'Thuê ngoài theo Cont' hoặc 'Thuê ngoài theo Xe - Tấn', bạn BẮT BUỘC phải nhập 'Bên vận chuyển' và 'Cảng hạ'!")
    
    def _get_note_invoice(self, lines):
        if not lines:
            return ""
        product_names = " + ".join(list(set(lines.mapped('product_id.name'))))
        container_names = ' + '.join(lines.mapped('container_number'))
        stk = self.custom_declaration_number or ""
        cang_ha_names = ' + '.join(list(set(lines.unload_container_id.mapped('name'))))
        qty_cont = len(lines)
        price_unit = lines[0].unload_container_id.standard_price
        total_amount = qty_cont * price_unit

        note = f"Cước vc {qty_cont} cont - {product_names} - {self.partner_id.name} - STK {stk} - {container_names} - {cang_ha_names}\nChi tiết: {qty_cont} x {price_unit:,.0f} = {total_amount:,.0f}"
        return note
    
    def action_create_delivery_cost(self):
        self.ensure_one()
        invoice_vals_list = []
        sequence = 10

        invoice_vals = self._prepare_invoice()
        if self.partner_unload_container_id:
            invoice_vals.update({
                'partner_id': self.partner_unload_container_id.id,
            })
            
        is_truck = False
        if hasattr(self, 'transportation_id') and self.transportation_id:
            if self.transportation_id.name == 'Thuê ngoài theo Xe - Tấn':
                is_truck = True

        if is_truck:
            total_qty = sum(self.order_line.mapped('qty_received'))
            if total_qty <= 0:
                total_qty = sum(self.order_line.mapped('product_qty'))
            
            if total_qty <= 0:
                raise UserError('Không có số lượng nhập kho để tính chi phí xe tải!')
            if not self.unload_container_id:
                raise UserError('Vui lòng chọn Cảng hạ / Dịch vụ vận chuyển!')

            product_names = " + ".join(list(set(self.order_line.mapped('product_id.name'))))
            dest_location = ""
            if self.picking_ids:
                dest_location = self.picking_ids[0].location_dest_id.name
            else:
                dest_location = self.picking_type_id.warehouse_id.name or ""

            price_unit = self.unload_container_id.standard_price
            total_amount = total_qty * price_unit

            note = f"Cước vận chuyển {total_qty} tấn - {product_names} - {self.partner_id.name} - {dest_location}\nChi tiết : {total_qty} x {price_unit:,.0f} = {total_amount:,.0f}"

            invoice_vals.update({
                'currency_id': self.company_id.currency_id.id,
                'note': note
            })

            parent_product = self.env['product.product'].search([
                ('unload_container_ids', 'in', [self.unload_container_id.product_tmpl_id.id])
            ], limit=1)
            
            if not parent_product:
                raise UserError('Không tìm thấy sản phẩm cha cho dịch vụ vận chuyển này!')

            line_vals = {
                'display_type': 'product',
                'name': note,
                'product_id': parent_product.id,
                'product_uom_id': parent_product.uom_po_id.id,
                'quantity': total_qty,
                'price_unit': price_unit,
                'tax_ids': [(6, 0, self.unload_container_id.supplier_taxes_id.ids)],
                'sequence': sequence
            }
            invoice_vals['invoice_line_ids'] = [(0, 0, line_vals)]

        else:
            lines = self.stock_input_ids.filtered(lambda l:l.state == 'done' and l.unload_container_id and not l.is_sale)
            if not lines:
                raise UserError('Không có dòng container nào hoàn tất hoặc chưa cấu hình Cảng hạ!')
            
            note = self._get_note_invoice(lines)
            invoice_vals.update({
                'currency_id': self.company_id.currency_id.id,
                'note': note
            })

            invoice_vals['invoice_line_ids'] = []
            for line in lines:
                line_vals = line._prepare_account_move_line()
                if line_vals:
                    line_vals['name'] = note
                    line_vals.update({'sequence': sequence})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    sequence += 1
        
        invoice_vals_list.append(invoice_vals)

        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            am = AccountMove.with_company(vals['company_id']).create(vals)
            moves |= am
            self.inv_unload_container_ids |= am

        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
        return self.action_view_invoice(moves)

    def action_view_unload_invoices(self):
        self.ensure_one()
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        result['domain'] = [('id', 'in', self.inv_unload_container_ids.ids)]
        result['context'] = {'default_move_type': 'in_invoice'}
        
        if len(self.inv_unload_container_ids) == 1:
            result['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            result['res_id'] = self.inv_unload_container_ids.id
            
        return result

    transport_ticket_ids = fields.One2many('transport.ticket', 'purchase_id', string='Phiếu vận chuyển')
    transport_ticket_count = fields.Integer(string='Số phiếu vận chuyển', compute='_compute_transport_ticket_count')
    inv_transport_cost_count = fields.Integer(string='Số Hóa đơn vận chuyển', compute='_compute_inv_transport_cost_count')
    transport_landed_cost_count = fields.Integer(string='Số phiếu trích trước', compute='_compute_transport_landed_cost_count')

    @api.depends('transport_ticket_ids.landed_cost_id')
    def _compute_transport_landed_cost_count(self):
        for order in self:
            order.transport_landed_cost_count = len(order.transport_ticket_ids.mapped('landed_cost_id'))

    def action_view_transport_landed_costs(self):
        self.ensure_one()
        lcs = self.transport_ticket_ids.mapped('landed_cost_id')
        moves = lcs.mapped('account_move_id')
        
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        result['domain'] = [('id', 'in', moves.ids)]
        result['name'] = 'Bút toán trích trước'
        
        if len(moves) == 1:
            result['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            result['res_id'] = moves.id
            
        return result

    @api.depends('transport_ticket_ids.move_id')
    def _compute_inv_transport_cost_count(self):
        for order in self:
            order.inv_transport_cost_count = len(order.transport_ticket_ids.mapped('move_id'))

    def action_view_transport_invoices(self):
        self.ensure_one()
        moves = self.transport_ticket_ids.mapped('move_id')
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        result['domain'] = [('id', 'in', moves.ids)]
        result['context'] = {'default_move_type': 'in_invoice'}
        
        if len(moves) == 1:
            result['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            result['res_id'] = moves.id
            
        return result

    @api.depends('transport_ticket_ids')
    def _compute_transport_ticket_count(self):
        for order in self:
            order.transport_ticket_count = len(order.transport_ticket_ids)

    def action_view_transport_tickets(self):
        self.ensure_one()
        return {
            'name': 'Phiếu vận chuyển',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.ticket',
            'view_mode': 'tree,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'default_purchase_id': self.id},
        }

    def action_create_transport_cost(self):
        self.ensure_one()
        tickets = self.transport_ticket_ids.filtered(lambda t: t.state == 'draft')
        if not tickets:
            raise UserError('Không có phiếu vận chuyển nào ở trạng thái Nháp để xuất hóa đơn!')

        is_truck = False
        if hasattr(self, 'transportation_id') and self.transportation_id:
            if self.transportation_id.name == 'Thuê ngoài theo Xe - Tấn':
                is_truck = True

        invoice_vals_list = []

        if is_truck:
            invoice_vals = self._prepare_invoice()
            if self.partner_unload_container_id:
                invoice_vals.update({'partner_id': self.partner_unload_container_id.id})
            invoice_vals.update({'currency_id': self.company_id.currency_id.id})

            total_qty = sum(tickets.mapped('quantity'))
            price_unit = tickets[0].price_unit if tickets else 0.0
            total_amount = total_qty * price_unit
            product_names = " + ".join(list(set(self.order_line.mapped('product_id.name'))))
            dest_location = self.picking_ids[0].location_dest_id.name if self.picking_ids else (self.picking_type_id.warehouse_id.name or "")
            note = f"Cước vận chuyển {total_qty} tấn - {product_names} - {self.partner_id.name} - {dest_location}\\nChi tiết : {total_qty} x {price_unit:,.0f} = {total_amount:,.0f}"

            invoice_vals.update({'note': note})
            invoice_lines = []
            sequence = 10
            for ticket in tickets:
                product = ticket.unload_container_id
                account_3351 = self.env['account.account'].search([
                    ('code', '=', '3351'), 
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                account_id = account_3351.id if account_3351 else (product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id.id)
                if not account_id:
                    raise UserError(f"Sản phẩm dịch vụ {product.name} chưa được cấu hình tài khoản chi phí!")

                line_vals = {
                    'display_type': 'product',
                    'name': note,
                    'product_id': product.id,
                    'product_uom_id': product.uom_po_id.id,
                    'account_id': account_id,
                    'quantity': ticket.quantity,
                    'price_unit': ticket.price_unit,
                    'tax_ids': [(6, 0, product.supplier_taxes_id.ids)],
                    'sequence': sequence
                }
                invoice_lines.append((0, 0, line_vals))
                sequence += 1
            invoice_vals['invoice_line_ids'] = invoice_lines
            invoice_vals_list.append((invoice_vals, tickets))

        else:
            # Container: group by picking to generate accurate notes
            pickings = tickets.mapped('picking_id')
            for picking in pickings:
                picking_tickets = tickets.filtered(lambda t: t.picking_id == picking)
                if not picking_tickets:
                    continue

                invoice_vals = self._prepare_invoice()
                if self.partner_unload_container_id:
                    invoice_vals.update({'partner_id': self.partner_unload_container_id.id})
                invoice_vals.update({'currency_id': self.company_id.currency_id.id})

                stock_inputs = self.stock_input_ids.filtered(lambda l: l.state == 'done' and l.unload_container_id and not l.is_sale and l.picking_id.id == picking.id)
                note = self._get_note_invoice(stock_inputs) if stock_inputs else "Chi phí vận chuyển"
                
                invoice_vals.update({'note': note})
                invoice_lines = []
                sequence = 10
                for ticket in picking_tickets:
                    product = ticket.unload_container_id
                    account_3351 = self.env['account.account'].search([
                        ('code', '=', '3351'), 
                        ('company_id', '=', self.company_id.id)
                    ], limit=1)
                    account_id = account_3351.id if account_3351 else (product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id.id)
                    if not account_id:
                        raise UserError(f"Sản phẩm dịch vụ {product.name} chưa được cấu hình tài khoản chi phí!")

                    line_vals = {
                        'display_type': 'product',
                        'name': note,
                        'product_id': product.id,
                        'product_uom_id': product.uom_po_id.id,
                        'account_id': account_id,
                        'quantity': ticket.quantity,
                        'price_unit': ticket.price_unit,
                        'tax_ids': [(6, 0, product.supplier_taxes_id.ids)],
                        'sequence': sequence
                    }
                    invoice_lines.append((0, 0, line_vals))
                    sequence += 1
                invoice_vals['invoice_line_ids'] = invoice_lines
                invoice_vals_list.append((invoice_vals, picking_tickets))

        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals, grp_tickets in invoice_vals_list:
            move = AccountMove.with_company(vals['company_id']).create(vals)
            moves |= move
            
            for idx, ticket in enumerate(grp_tickets):
                matching_line = move.invoice_line_ids.filtered(lambda l: l.sequence == 10 + idx)
                if matching_line:
                    ticket.write({
                        'move_line_id': matching_line[0].id,
                        'state': 'invoiced',
                    })

        self.inv_unload_container_ids |= moves
        
        return self.action_view_invoice(moves)
