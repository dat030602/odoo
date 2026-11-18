# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    misa_einvoice_id = fields.Many2one(
        'misa.einvoice.document',
        string='MISA e-Invoice',
        readonly=True,
        copy=False,
        help='Active MISA e-Invoice document associated with this POS order'
    )
    misa_einvoice_ids = fields.One2many(
        'misa.einvoice.document',
        'pos_order_id',
        string='MISA e-Invoices',
        help='History of MISA e-Invoices generated for this POS order'
    )
    misa_einvoice_count = fields.Integer(
        string='MISA e-Invoice Count',
        compute='_compute_misa_einvoice_count'
    )

    @api.depends('misa_einvoice_ids')
    def _compute_misa_einvoice_count(self):
        for order in self:
            order.misa_einvoice_count = len(order.misa_einvoice_ids)

    def action_create_misa_einvoice_document(self):
        """Create a decoupled misa.einvoice.document from this pos.order."""
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id

        # Find matching Cash Register template (series with 'M') or default POS template
        template = self.env['misa.invoice.template'].search([
            ('company_id', '=', company.id),
            ('invoice_system_type', '=', 'M'),
            ('inactive', '=', False),
        ], limit=1)

        if not template:
            template = self.env['misa.invoice.template'].search([
                ('company_id', '=', company.id),
                ('inactive', '=', False),
            ], limit=1)

        inv_series = template.inv_series if template else '1C26MYY'
        inv_template_no = template.inv_template_no if template else '1'

        buyer_legal_name = partner.commercial_company_name or partner.name if partner else _('Retail Customer')
        buyer_address = partner.contact_address if partner else _('Retail Store')

        doc_vals = {
            'pos_order_id': self.id,
            'company_id': company.id,
            'currency_id': self.currency_id.id,
            'exchange_rate': 1.0,
            'inv_series': inv_series,
            'inv_template_no': inv_template_no,
            'inv_date': fields.Date.context_today(self),
            'sign_type': '5',  # Cash register MTT flow
            'reference_type': '0',
            'buyer_code': partner.ref if partner else '',
            'buyer_legal_name': buyer_legal_name,
            'buyer_tax_code': (partner.vat or '').strip() if partner else '',
            'buyer_address': buyer_address,
            'buyer_full_name': partner.name if partner else _('Retail Customer'),
            'buyer_phone_number': (partner.phone or partner.mobile) if partner else '',
            'buyer_email': partner.email if partner else '',
            'payment_method_name': 'TM/CK',
        }

        # Build lines
        lines_vals = []
        line_num = 1
        for pos_line in self.lines:
            price_subtotal = pos_line.price_subtotal
            price_total = pos_line.price_subtotal_incl
            vat_amount = price_total - price_subtotal
            tax_name = pos_line.tax_ids[0].name if pos_line.tax_ids else 'KHONGTHUE'

            lines_vals.append((0, 0, {
                'line_number': line_num,
                'sort_order': line_num,
                'item_type': '1',
                'item_code': pos_line.product_id.default_code or '',
                'item_name': pos_line.product_id.name or 'Item',
                'unit_name': pos_line.product_uom_id.name or '',
                'quantity': pos_line.qty,
                'unit_price': pos_line.price_unit,
                'amount_oc': pos_line.qty * pos_line.price_unit,
                'discount_rate': pos_line.discount,
                'discount_amount_oc': (pos_line.qty * pos_line.price_unit) * (pos_line.discount / 100.0) if pos_line.discount else 0.0,
                'amount_without_vat_oc': price_subtotal,
                'vat_rate_name': tax_name,
                'vat_amount_oc': vat_amount,
            }))
            line_num += 1

        doc_vals['line_ids'] = lines_vals
        doc = self.env['misa.einvoice.document'].create(doc_vals)
        self.misa_einvoice_id = doc.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('MISA e-Invoice Document'),
            'res_model': 'misa.einvoice.document',
            'res_id': doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_misa_einvoice_documents(self):
        """View all MISA e-Invoice documents linked to this pos.order."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dn_misa_connector_meinvoice.action_misa_einvoice_document')
        action['domain'] = [('pos_order_id', '=', self.id)]
        action['context'] = {'default_pos_order_id': self.id}
        return action
