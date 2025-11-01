# -*- coding: utf-8 -*-
import logging
import uuid
from itertools import groupby
from operator import itemgetter

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('viettel_sinvoice_ids')
    def _compute_sinvoices_count(self):
        for move in self:
            move.sinvoice_count = len(move.viettel_sinvoice_ids)

    partner_contact_id = fields.Many2one('res.partner', 'S-Invoice Contact', tracking=True)
    partner_vat_id = fields.Many2one('res.partner', 'Legal S-invoice Customer', tracking=True,
                                     domain="[('is_company','=',True)]")
    viettel_sinvoice_ids = fields.Many2many('viettel.sinvoice', 'viettel_sinvoice_account_rel', string='Viettel S-invoice', copy=False)

    sinvoice_ref = fields.Char('S-Invoice Reference', compute='_compute_sinvoice_reference', store=False)
    sinvoice_date = fields.Datetime('S-Invoice Date', readonly=True)
    sinvoice_count = fields.Integer('S-Invoices Count', compute='_compute_sinvoice_reference')
    default_viettel_sinvoice_template_id = fields.Many2one('viettel.sinvoice.template', 'Default Template')

    @api.onchange('team_id')
    def _onchange_team_id(self):
        for move in self:
            if move.team_id:
                move.default_viettel_sinvoice_template_id = self.team_id.default_viettel_sinvoice_template_id

    @api.depends('viettel_sinvoice_ids')
    def _compute_sinvoice_reference(self):
        for move in self:
            move.sinvoice_ref = ' - '.join(move.viettel_sinvoice_ids.filtered(lambda s: s.state not in ('draft', 'confirm')).mapped('name'))
            move.sinvoice_count = len(move.viettel_sinvoice_ids)

    def unlink(self):
        for move in self:
            if move.viettel_sinvoice_ids.filtered(lambda s: s.state not in ('draft', 'confirm')):
                raise UserError(_("Bạn không thể xoá bút toán đã Phát hành hoá đơn điện tử."))
            self.viettel_sinvoice_ids.unlink()
        return super(AccountMove, self).unlink()

    def _prepare_sinvoice_line_values(self):
        line_vals = []
        for line in self.invoice_line_ids:
            if line.display_type != 'product' or not line.product_id:
                continue
            name = line.product_id.name or ''
            val = {
                'name': name,
                'origin': name,
                'account_id': line.account_id.id,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'discount': line.discount,
                'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id or False,
                'sinvoice_line_tax_id': line.tax_ids.ids[0] if line.tax_ids else False,
            }
            if float_compare(line.price_unit * line.quantity, 0, 0) == -1:
                val['selection'] = '3'
            else:
                val['selection'] = '1'

            line_vals.append(val)

        format_list_results = []
        if len(self) > 1:
            group_keys = [
                'selection', 'name', 'origin', 'account_id', 'price_unit', 'discount', 'uom_id', 'product_id',
                'sinvoice_line_tax_id']
            grouper = itemgetter(*group_keys)
            grouped_rslt = []
            for keys, grouped_values in groupby(sorted(line_vals, key=grouper), key=grouper):
                items = dict(zip(group_keys, keys))
                items['quantity'] = sum([item["quantity"] for item in grouped_values])
                grouped_rslt.append(items)
            for item in grouped_rslt:
                format_list_results.append((0, 0, item))
        else:
            for item in line_vals:
                format_list_results.append((0, 0, item))
        return format_list_results

    def get_default_viettel_sinvoice_template(self):
        return self.env['viettel.sinvoice.template'].search([('company_id', '=', self.env.company.id)], limit=1).id

    def create_data_sinvoice(self):
        if not self:
            return
        if any(not move.partner_vat_id and not move.partner_contact_id for move in self):
            raise UserError("You must select a customer for invoicing !")
        if len(self.mapped('partner_vat_id')) > 1:
            raise UserError('Các Hóa đơn phải cùng một Đơn vị xuất hóa đơn !')
        if any(inv.state != 'posted' for inv in self):
            raise UserError(_('Invoice Must be in Post State..'))
        if any(inv.move_type != 'out_invoice' for inv in self):
            raise UserError(_("Chỉ hỗ trợ tạo hóa đơn điện tử cho công nợ của khách hàng."))

        invoice = self[0]
        sinvoice_val = {
            'partner_id': invoice.partner_contact_id and invoice.partner_contact_id.id or False,
            'partner_vat_id': invoice.partner_vat_id and invoice.partner_vat_id.id or False,
            'date_invoice': invoice.invoice_date,
            'date': invoice.date,
            'company_id': invoice.company_id.id,
            'journal_id': invoice.journal_id.id,
            'company_currency_id': invoice.company_currency_id.id,
            'fiscal_position_id': invoice.fiscal_position_id and invoice.fiscal_position_id.id,
            'internal_move_type': invoice.move_type,
            'payment_term_id': invoice.invoice_payment_term_id.id,
            'paymentStatus': invoice.payment_state in ('in_payment', 'paid', 'partial') or False,
            'invoice_ids': [(4, move.id) for move in self],
            # S-Invoice Data Information
            'invoiceIssuedDate': fields.Datetime.now(),
            'adjustmentType': '1',
            'transactionID': str(uuid.uuid4()),
            'viettel_sinvoice_template_id': self.get_default_viettel_sinvoice_template() or False,
        }
        sinvoice_line_vals = self._prepare_sinvoice_line_values()
        sinvoice_val['sinvoice_line'] = sinvoice_line_vals
        sinvoice_id = self.env['viettel.sinvoice'].create(sinvoice_val)
        self.viettel_sinvoice_ids |= sinvoice_id
        return sinvoice_id

    def action_create_data_sinvoice(self):
        sinvoice_id = self.create_data_sinvoice()
        view = self.env.ref('viettel_sinvoice.view_viettel_sinvoice_form')
        return {
            'name': _('S-Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'viettel.sinvoice',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': sinvoice_id.id,
            'context': dict(self.env.context, create=False)
        }
