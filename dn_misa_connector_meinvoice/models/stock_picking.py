# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    misa_einvoice_id = fields.Many2one(
        'misa.einvoice.document',
        string='MISA Stock Delivery Note (PXK)',
        readonly=True,
        copy=False,
        help='Active MISA Electronic Stock Delivery Note (PXK) document'
    )
    misa_einvoice_ids = fields.One2many(
        'misa.einvoice.document',
        'picking_id',
        string='MISA Stock Delivery Notes',
        help='History of MISA Stock Delivery Notes generated for this picking'
    )
    misa_einvoice_count = fields.Integer(
        string='MISA PXK Count',
        compute='_compute_misa_einvoice_count'
    )

    @api.depends('misa_einvoice_ids')
    def _compute_misa_einvoice_count(self):
        for picking in self:
            picking.misa_einvoice_count = len(picking.misa_einvoice_ids)

    def action_create_misa_einvoice_document(self):
        """Create a decoupled misa.einvoice.document for Stock Delivery Note (PXK)."""
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id or self.picking_type_id.warehouse_id.partner_id

        # Find template with series starting with '6' (PXK)
        template = self.env['misa.invoice.template'].search([
            ('company_id', '=', company.id),
            ('invoice_type', '=', '6'),
            ('inactive', '=', False),
        ], limit=1)

        inv_series = template.inv_series if template else '6C26TAA'
        inv_template_no = template.inv_template_no if template else '1'

        doc_vals = {
            'picking_id': self.id,
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'exchange_rate': 1.0,
            'inv_series': inv_series,
            'inv_template_no': inv_template_no,
            'inv_date': fields.Date.context_today(self),
            'reference_type': '0',
            # Stock Delivery specifics
            'stock_out_legal_name': company.name,
            'stock_out_tax_code': company.misa_tax_code,
            'stock_out_address': company.partner_id.contact_address,
            'stock_out_full_name': self.env.user.name,
            'internal_command': _('Internal Stock Transfer Order'),
            'internal_command_no': self.origin or self.name,
            'internal_command_owner': self.env.user.name,
            'internal_command_date': fields.Date.context_today(self),
            'stock_in_legal_name': partner.commercial_company_name or partner.name or company.name,
            'stock_in_tax_code': (partner.vat or '').strip() if partner else '',
            'stock_in_address': partner.contact_address if partner else '',
            'stock_in_full_name': partner.name if partner else '',
            'journal_memo': self.note or _('Stock Dispatch Transfer %s') % self.name,
            # Buyer header
            'buyer_code': partner.ref if partner else '',
            'buyer_legal_name': partner.commercial_company_name or partner.name or company.name,
            'buyer_tax_code': (partner.vat or '').strip() if partner else '',
            'buyer_address': partner.contact_address if partner else company.partner_id.contact_address,
            'payment_method_name': 'TM/CK',
        }

        # Build lines
        lines_vals = []
        line_num = 1
        for move in self.move_ids.filtered(lambda m: m.state == 'done' or m.quantity > 0):
            qty = move.quantity or move.product_uom_qty
            unit_price = move.product_id.standard_price or 0.0

            lines_vals.append((0, 0, {
                'line_number': line_num,
                'sort_order': line_num,
                'item_type': '1',
                'item_code': move.product_id.default_code or '',
                'item_name': move.product_id.name or 'Item',
                'unit_name': move.product_uom.name or '',
                'quantity': qty,
                'unit_price': unit_price,
                'amount_oc': qty * unit_price,
                'amount_without_vat_oc': qty * unit_price,
                'vat_rate_name': 'KHONGTHUE',
                'vat_amount_oc': 0.0,
            }))
            line_num += 1

        doc_vals['line_ids'] = lines_vals
        doc = self.env['misa.einvoice.document'].create(doc_vals)
        self.misa_einvoice_id = doc.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('MISA Stock Delivery Note (PXK)'),
            'res_model': 'misa.einvoice.document',
            'res_id': doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_misa_einvoice_documents(self):
        """View all MISA Stock Delivery Notes linked to this picking."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dn_misa_connector_meinvoice.action_misa_einvoice_document')
        action['domain'] = [('picking_id', '=', self.id)]
        action['context'] = {'default_picking_id': self.id}
        return action
