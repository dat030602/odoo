from odoo import models, fields, api, _
import re
import unidecode
from rapidfuzz import process
import logging

_logger = logging.getLogger(__name__)


def normalize_name(name):
    """Normalize product name (lowercase, remove accents, standardize separators)."""
    if not name:
        return ""
    name = name.lower()
    name = unidecode.unidecode(name)  # remove accents
    name = re.sub(r'[\s\*xX\-]+', 'x', name)  # standardize x/*/-
    name = re.sub(r'\s+', ' ', name).strip()
    return name


class GdtEinvoiceLine(models.Model):
    _name = 'gdt.einvoice.line'
    _description = 'Invoice Line'
    _order = 'id'

    # ========== Basic Fields ==========
    parent_id = fields.Many2one('gdt.einvoice', string='Invoice', ondelete='cascade', required=True)
    name = fields.Char(string='Label')
    unit = fields.Char(string='Unit of Measure')

    # ========== Product Information ==========
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_product_id', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom')

    # ========== Quantity Information ==========
    quantity = fields.Float(string='Quantity', default=1.0, digits="Product Unit of Measure")
    qty_to_invoice = fields.Float(string='Quantity to Invoice', compute='_compute_qty_to_invoice')

    # ========== Price Information ==========
    unit_price = fields.Monetary(string='Unit Price')
    currency_id = fields.Many2one("res.currency", string="Currency", related="parent_id.currency_id")

    # ========== Tax Information ==========
    tax_rate = fields.Float(string='Tax Rate', default=0)
    tax_id = fields.Many2one('account.tax', string='Tax', compute='_compute_tax_id')

    # ========== Computed Price Fields ==========
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_price_total', store=True)
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_price_total', store=True)
    price_total = fields.Monetary(string='Total', compute='_compute_price_total', store=True)

    # ========== Compute Methods ==========
    @api.depends('name')
    def _compute_product_id(self):
        """Auto-assign product based on name using mapping and fuzzy search"""
        for record in self:
            selected_product = False
            name_to_check = (record.name or "").lower()
            mapping_products = self.env['gdt.map.product'].search([])

            for mapping in mapping_products:
                if not mapping.keyword:
                    continue
                keywords = [kw.strip().lower() for kw in mapping.keyword.split(',')]
                if any(keyword and keyword in name_to_check for keyword in keywords):
                    if mapping.product_id:
                        selected_product = mapping.product_id
                        break

            if not selected_product:
                selected_product = record.fuzzy_find_product(name_to_check)

            if not selected_product:
                selected_product = self.env['gdt.map.product'].search([], limit=1).mapped('product_id')

            record.product_id = selected_product

    @api.depends("unit", "parent_id.move_type", "product_id")
    def _compute_uom(self):
        """Compute unit of measure based on product and invoice type"""
        for rec in self:
            uom_id = False
            if rec.parent_id.move_type in ['out_invoice', 'out_refund']:
                uom_id = rec.product_id.uom_id if rec.product_id.uom_id else self.env['uom.uom'].search([('name', '=', rec.unit)], limit=1)
            elif rec.parent_id.move_type in ['in_invoice', 'in_refund']:
                uom_id = rec.product_id.uom_po_id if rec.product_id.uom_po_id else self.env['uom.uom'].search([('name', '=', rec.unit)], limit=1)
            rec.uom_id = uom_id

    @api.depends('quantity', 'parent_id.invoice_line_ids', 'parent_id.invoice_ids')
    def _compute_qty_to_invoice(self):
        """Compute remaining quantity to invoice"""
        for record in self:
            invoiced_qty = sum(record.parent_id.invoice_ids.invoice_line_ids.filtered(
                lambda l: l.product_id == record.product_id
            ).mapped('quantity'))
            record.qty_to_invoice = max(record.quantity - invoiced_qty, 0)

    @api.depends('tax_rate', 'parent_id.move_type')
    def _compute_tax_id(self):
        """Compute tax based on tax rate and invoice type"""
        for record in self:
            tax_id = False
            if record.tax_rate:
                if record.parent_id.move_type in ['out_invoice', 'out_refund']:
                    tax_id = self.env['account.tax'].search([
                        ('amount', '=', record.tax_rate),
                        ('type_tax_use', '=', 'sale')
                    ], limit=1)
                elif record.parent_id.move_type in ['in_invoice', 'in_refund']:
                    tax_id = self.env['account.tax'].search([
                        ('amount', '=', record.tax_rate),
                        ('type_tax_use', '=', 'purchase')
                    ], limit=1)
            record.tax_id = tax_id

    @api.depends('quantity', 'unit_price', 'tax_id', 'parent_id.move_type', 'parent_id.partner_buyer_id', 'parent_id.partner_seller_id')
    def _compute_price_total(self):
        """Compute price totals including tax"""
        for record in self:
            partner_id = record.parent_id.partner_buyer_id if record.parent_id.move_type in ['out_invoice', 'out_refund'] else record.parent_id.partner_seller_id
            if record.tax_id:
                taxes = record.tax_id.compute_all(
                    record.unit_price,
                    quantity=record.quantity,
                    product=record.product_id,
                    partner=partner_id
                )
                record.price_subtotal = taxes['total_excluded']
                record.price_tax = taxes['total_included'] - taxes['total_excluded']
                record.price_total = taxes['total_included']
            else:
                record.price_subtotal = record.unit_price * record.quantity
                record.price_tax = 0.0
                record.price_total = record.price_subtotal

    # ========== Helper Methods ==========
    def fuzzy_find_product(self, supplier_name, threshold=80):
        """
        Find product by fuzzy matching supplier name.
        :param supplier_name: product name from supplier (str)
        :param threshold: minimum match threshold (0-100)
        :return: product.product record or None
        """
        supplier_norm = normalize_name(supplier_name)
        products = self.env['product.product'].search([])
        product_names = {normalize_name(p.name): p.id for p in products}
        match = process.extractOne(supplier_norm, product_names.keys())

        if match:
            matched_name, score, _ = match
            if score >= threshold:
                return self.env['product.product'].browse(product_names[matched_name])
        return None

    def _convert_to_tax_base_line_dict(self, partner=None, **kwargs):
        """Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :param partner: Partner to use for tax computation
        :return: A python dictionary.
        """
        self.ensure_one()
        if not partner:
            partner = self.parent_id.partner_buyer_id if self.parent_id.move_type in ['out_invoice', 'out_refund'] else self.parent_id.partner_seller_id
        
        # Ensure price_subtotal is computed, fallback to unit_price * quantity if not
        price_subtotal = self.price_subtotal
        if not price_subtotal and self.unit_price and self.quantity:
            price_subtotal = self.unit_price * self.quantity
        
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=partner or self.env['res.partner'],
            currency=self.currency_id or self.parent_id.currency_id or self.env.company.currency_id,
            product=self.product_id or self.env['product.product'],
            taxes=self.tax_id or self.env['account.tax'],
            price_unit=self.unit_price or 0.0,
            quantity=self.quantity or 0.0,
            discount=0.0,
            price_subtotal=price_subtotal or 0.0,
            **kwargs,
        )

    def create_data_mapping_product(self):
        """Create product mapping if not exists"""
        for record in self:
            if self.env['gdt.map.product'].search_count([('keyword', '=', record.name)]):
                continue
            self.env['gdt.map.product'].create({
                'keyword': record.name,
                'product_id': record.product_id.id,
                'create_auto': True,
            })

