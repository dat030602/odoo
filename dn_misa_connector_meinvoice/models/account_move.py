# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    misa_einvoice_id = fields.Many2one(
        'misa.einvoice.document',
        string='MISA e-Invoice',
        readonly=True,
        copy=False,
        help='Active MISA e-Invoice document associated with this invoice'
    )
    misa_einvoice_ids = fields.One2many(
        'misa.einvoice.document',
        'move_id',
        string='MISA e-Invoices',
        help='History of MISA e-Invoice documents generated for this accounting move'
    )
    misa_einvoice_count = fields.Integer(
        string='e-Invoice Count',
        compute='_compute_misa_einvoice_count'
    )

    @api.depends('misa_einvoice_ids')
    def _compute_misa_einvoice_count(self):
        for move in self:
            move.misa_einvoice_count = len(move.misa_einvoice_ids)

    def action_create_misa_einvoice_document(self):
        """Create a decoupled misa.einvoice.document record from this account.move."""
        self.ensure_one()
        if self.move_type not in ['out_invoice', 'out_refund']:
            raise UserError(_("MISA e-Invoices can only be issued for Customer Invoices or Credit Notes."))

        partner = self.partner_id
        company = self.company_id

        # Find matching template for series
        template = self.env['misa.invoice.template'].search([
            ('company_id', '=', company.id),
            ('inactive', '=', False),
        ], limit=1)

        inv_series = template.inv_series if template else '1C26TYY'
        inv_template_no = template.inv_template_no if template else '1'

        # Reference type (out_refund => adjustment / replacement)
        ref_type = '2' if self.move_type == 'out_refund' else '0'

        doc_vals = {
            'move_id': self.id,
            'company_id': company.id,
            'currency_id': self.currency_id.id,
            'exchange_rate': 1.0,
            'inv_series': inv_series,
            'inv_template_no': inv_template_no,
            'inv_date': self.invoice_date or fields.Date.context_today(self),
            'reference_type': ref_type,
            'adjust_replace_reason_code': '13' if ref_type == '2' else False,
            'buyer_code': partner.ref or '',
            'buyer_legal_name': partner.commercial_company_name or partner.name or '',
            'buyer_tax_code': (partner.vat or '').strip(),
            'buyer_address': partner.contact_address or '',
            'buyer_full_name': partner.name or '',
            'buyer_phone_number': partner.phone or partner.mobile or '',
            'buyer_email': partner.email or '',
            'buyer_bank_account': partner.bank_ids[0].acc_number if partner.bank_ids else '',
            'buyer_bank_name': partner.bank_ids[0].bank_name if partner.bank_ids else '',
            'payment_method_name': 'TM/CK',
        }

        # Build lines
        lines_vals = []
        line_num = 1
        for inv_line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            price_subtotal = inv_line.price_subtotal
            price_total = inv_line.price_total
            vat_amount = price_total - price_subtotal

            tax_name = inv_line.tax_ids[0].name if inv_line.tax_ids else 'KHONGTHUE'

            lines_vals.append((0, 0, {
                'line_number': line_num,
                'sort_order': line_num,
                'item_type': '1',
                'item_code': inv_line.product_id.default_code or '',
                'item_name': inv_line.name or inv_line.product_id.name or 'Item',
                'unit_name': inv_line.product_uom_id.name or '',
                'quantity': inv_line.quantity,
                'unit_price': inv_line.price_unit,
                'amount_oc': inv_line.quantity * inv_line.price_unit,
                'discount_rate': inv_line.discount,
                'discount_amount_oc': (inv_line.quantity * inv_line.price_unit) * (inv_line.discount / 100.0) if inv_line.discount else 0.0,
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
        """View all MISA e-Invoice documents linked to this move."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dn_misa_connector_meinvoice.action_misa_einvoice_document')
        action['domain'] = [('move_id', '=', self.id)]
        action['context'] = {'default_move_id': self.id}
        return action
