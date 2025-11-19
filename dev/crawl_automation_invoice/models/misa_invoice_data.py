from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class MisaInvoiceData(models.Model):
    _name = 'misa.invoice.data'
    _description = 'Invoice Data'
    _rec_name = 'invoice_date'
    _order = 'invoice_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ========== Basic Fields ==========
    name = fields.Char(string='Invoice Name', compute='_compute_name', store=True)
    invoice_code = fields.Char(string='Invoice Code', required=True, tracking=True)
    invoice_number = fields.Char(string='Invoice Number', required=True, index=True, tracking=True)
    invoice_date = fields.Date(string='Invoice Date', required=True, index=True, tracking=True)
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
    ], string='Invoice Type', default='in_invoice', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done'),
    ], string='Status', compute='_compute_state', store=True, tracking=True)

    # ========== Seller Information ==========
    seller_name = fields.Char(string='Seller Name', tracking=True)
    seller_tax_code = fields.Char(string='Seller Tax Code', tracking=True)
    seller_address = fields.Text(string='Seller Address', tracking=True)
    partner_seller_id = fields.Many2one('res.partner', string='Seller', compute='_compute_partner_seller_id')

    # ========== Buyer Information ==========
    buyer_name = fields.Char(string='Buyer Name', tracking=True)
    buyer_tax_code = fields.Char(string='Buyer Tax Code', tracking=True)
    buyer_address = fields.Text(string='Buyer Address', tracking=True)
    partner_buyer_id = fields.Many2one('res.partner', string='Buyer', compute='_compute_partner_buyer_id')

    # ========== Currency Information ==========
    currency_name = fields.Char(string='Currency Name', tracking=True)
    currency_rate = fields.Float(string='Currency Rate', default=1.0, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id', tracking=True)

    # ========== Related Orders ==========
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', tracking=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', tracking=True)

    # ========== Relations ==========
    invoice_line_ids = fields.One2many('misa.invoice.data.line', 'parent_id', string='Invoice Lines')
    invoice_ids = fields.Many2many('account.move', string='Invoices', compute='_compute_invoice_ids', store=True)

    # ========== Tax Totals ==========
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)

    # ========== Note Information ==========
    note = fields.Text(string='Note', tracking=True)

    # ========== Compute Methods ==========
    @api.depends('invoice_code', 'invoice_number')
    def _compute_name(self):
        for record in self:
            if record.invoice_code and record.invoice_number:
                record.name = f"{record.invoice_code}{record.invoice_number}"
            else:
                record.name = False

    @api.depends('currency_name')
    def _compute_currency_id(self):
        for record in self:
            if record.currency_name:
                record.currency_id = self.env['res.currency'].search([('name', '=', record.currency_name)], limit=1)
            else:
                record.currency_id = self.env.ref('base.VND')

    @api.depends('invoice_code', 'invoice_number')
    def _compute_invoice_ids(self):
        for record in self:
            record.invoice_ids = self.env['account.move'].search([('ref', '=', record.name)])

    @api.depends('invoice_line_ids.product_id', 'invoice_ids.state')
    def _compute_state(self):
        for record in self:
            if all(invoice.state == 'posted' for invoice in record.invoice_ids):
                record.state = 'done'
            elif record.invoice_line_ids.mapped('product_id'):
                record.state = 'processing'
            else:
                record.state = 'draft'

    @api.depends('seller_tax_code')
    def _compute_partner_seller_id(self):
        """Automatically assign seller based on tax code"""
        for record in self:
            if record.seller_tax_code:
                partner = self.env['res.partner'].search([('vat', '=', record.seller_tax_code)], limit=1)
                record.partner_seller_id = partner.id if partner else False
            else:
                record.partner_seller_id = False

    @api.depends('buyer_tax_code')
    def _compute_partner_buyer_id(self):
        """Automatically assign buyer based on tax code"""
        for record in self:
            if record.buyer_tax_code:
                partner = self.env['res.partner'].search([('vat', '=', record.buyer_tax_code)], limit=1)
                record.partner_buyer_id = partner.id if partner else False
            else:
                record.partner_buyer_id = False

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.price_tax', 'invoice_line_ids.tax_id')
    def _compute_tax_totals(self):
        """Compute tax totals from invoice lines"""
        for record in self:
            record = record.with_company(record.env.company)
            invoice_lines = record.invoice_line_ids.filtered(lambda l: l.product_id)
            currency = record.currency_id or record.env.company.currency_id
            
            # Get partner based on move_type
            partner = record.partner_buyer_id if record.move_type in ['out_invoice', 'out_refund'] else record.partner_seller_id
            
            # Convert invoice lines to tax base line dicts
            tax_base_lines = [
                line._convert_to_tax_base_line_dict(partner=partner)
                for line in invoice_lines
            ]
            
            # Always call _prepare_tax_totals, even with empty list, to get valid structure
            record.tax_totals = self.env['account.tax']._prepare_tax_totals(
                tax_base_lines,
                currency,
            )

    # ========== Action Methods ==========
    def action_create_partner_seller(self):
        self.ensure_one()
        default_vals = {
            'company_type': 'company',
            'vat': self.seller_tax_code,
            'name': self.seller_name,
            'street': self.seller_address
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Partner',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'target': 'new',
            'context': {**self.env.context, **{'default_%s' % k: v for k, v in default_vals.items()}},
            'res_id': False,
            'views': [[self.env.ref('base.view_partner_form').id, 'form']],
        }

    def action_create_partner_buyer(self):
        self.ensure_one()
        default_vals = {
            'company_type': 'company',
            'vat': self.buyer_tax_code,
            'name': self.buyer_name,
            'street': self.buyer_address
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Partner',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'target': 'new',
            'context': {**self.env.context, **{'default_%s' % k: v for k, v in default_vals.items()}},
            'res_id': False,
            'views': [[self.env.ref('base.view_partner_form').id, 'form']],
        }

    def action_find_product(self):
        """Find and assign products to invoice lines"""
        for record in self:
            for line in record.invoice_line_ids:
                product_name_lower = line.name.lower()
                selected_product = False
                mapping_products = self.env['misa.map.product'].search([('active', '=', True)])
                for mapping in mapping_products:
                    if mapping.keyword:
                        keywords = [kw.strip().lower() for kw in mapping.keyword.split(',')]
                        for keyword in keywords:
                            if keyword and keyword in product_name_lower:
                                if mapping.product_id:
                                    selected_product = mapping.product_id
                                    break
                        if selected_product:
                            break

                if not selected_product:
                    selected_product = line.fuzzy_find_product(line.name)
                if not selected_product:
                    selected_product = self.env['misa.map.product'].search([], limit=1).mapped('product_id')
                line.product_id = selected_product

    def action_create_invoice(self):
        """Create invoice from current data"""
        self.ensure_one()
        if self.move_type in ['out_invoice', 'out_refund'] and self.partner_buyer_id:
            return self.create_invoice_out()
        elif self.move_type in ['in_invoice', 'in_refund'] and self.partner_seller_id:
            return self.create_invoice_in()
        else:
            raise ValidationError(_("Cannot create invoice: Missing seller or buyer or invalid invoice type"))

    def action_view_invoice(self):
        """Open list of created invoices"""
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if self.move_type == 'out_refund':
            action = self.env.ref('account.action_move_out_refund_type').sudo().read()[0]
        elif self.move_type == 'in_invoice':
            action = self.env.ref('account.action_move_in_invoice_type').sudo().read()[0]
        elif self.move_type == 'in_refund':
            action = self.env.ref('account.action_move_in_refund_type').sudo().read()[0]
        action['domain'] = [('ref', '=', self.name)]
        return action

    # ========== Private Methods ==========
    def create_invoice_out(self):
        """Create customer invoice"""
        self.ensure_one()
        if not self.sale_order_id:
            raise ValidationError(_("Cannot create invoice: Missing sale order"))
        invoice = self.sale_order_id._prepare_invoice()
        invoice['partner_id'] = self.partner_buyer_id.id
        invoice['date'] = self.invoice_date
        invoice['invoice_date'] = self.invoice_date
        invoice['ref'] = self.name
        invoice_lines = []
        for invoice_line in self.invoice_line_ids:
            order_line = self.sale_order_id.order_line.filtered(lambda l: l.product_id == invoice_line.product_id)
            invoice_val = order_line._prepare_invoice_line()
            invoice_line['quantity'] = min(invoice_line.qty_to_invoice, self.invoice_line_ids.filtered(lambda l: l.product_id == invoice_line.product_id).quantity)
            invoice_line['price_unit'] = invoice_line.unit_price
            invoice_line['tax_ids'] = [Command.set(invoice_line.tax_id.ids)]
            invoice_line.create_data_mapping_product()
            invoice_lines.append(invoice_val)
        invoice['invoice_line_ids'] = invoice_lines
        invoice = self.env['account.move'].create(invoice)
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        action['res_id'] = invoice.id
        action['view_mode'] = 'form'
        action['views'] = [[False, 'form']]
        return action

    def create_invoice_in(self):
        """Create vendor bill"""
        self.ensure_one()
        if not self.purchase_order_id:
            raise ValidationError(_("Cannot create invoice: Missing purchase order"))
        invoice = self.purchase_order_id._prepare_invoice()
        invoice['partner_id'] = self.partner_seller_id.id
        invoice['date'] = self.invoice_date
        invoice['invoice_date'] = self.invoice_date
        invoice['ref'] = self.name
        invoice_lines = []
        for invoice_line in self.invoice_line_ids:
            order_line = self.purchase_order_id.order_line.filtered(lambda l: l.product_id == invoice_line.product_id)
            invoice_val = order_line._prepare_account_move_line(move=invoice)
            invoice_line['quantity'] = min(invoice_line.qty_to_invoice, self.invoice_line_ids.filtered(lambda l: l.product_id == invoice_line.product_id).quantity)
            invoice_line['price_unit'] = invoice_line.unit_price
            invoice_line['tax_ids'] = [Command.set(invoice_line.tax_id.ids)]
            invoice_line.create_data_mapping_product()
            invoice_lines.append(invoice_val)
        invoice['invoice_line_ids'] = invoice_lines
        invoice = self.env['account.move'].create(invoice)
        action = self.env.ref('account.action_move_in_invoice_type').sudo().read()[0]
        action['res_id'] = invoice.id
        action['view_mode'] = 'form'
        action['views'] = [[False, 'form']]
        return action

    def _get_invoice_data(self):
        return [
            {
                "invoice_code": invoice.invoice_code or '',
                "invoice_number": invoice.invoice_number or '',
                "invoice_date": invoice.invoice_date.strftime('%Y-%m-%d') or '',
                "seller_name": invoice.seller_name or '',
                "seller_vat": invoice.seller_tax_code or '',
                "seller_address": invoice.seller_address or '',
                "buyer_name": invoice.buyer_name or '',
                "buyer_vat": invoice.buyer_tax_code or '',
                "buyer_address": invoice.buyer_address or '',
                "note": invoice.note or '',
                "line_ids": [
                    {
                        "name": line.name or '',
                        "quantity": line.quantity,
                        "unit_price": line.unit_price,
                        "unit": line.unit or '',
                        "total": line.price_subtotal or '',
                        "tax_rate": line.tax_rate or '',
                    }
                for line in invoice.invoice_line_ids],
            }
        for invoice in self.search([])]
