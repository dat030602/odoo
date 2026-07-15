from collections import defaultdict
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
from odoo.fields import Command
import logging

from odoo.tools import formatLang

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    move_tax_import_id = fields.Many2one("account.move", string="Bút toán thuế nhập khẩu")

    def _post(self, soft=True):
        for move in self:
            if move.move_type in ('in_invoice', 'in_receipt', 'in_refund') and not move.payment_reference and move.note:
                move.payment_reference = move.note
        res = super(AccountMove, self)._post(soft)
        for move in self.sudo():
            if move.stock_valuation_layer_ids:
                link = False
                stock_moves = move.stock_valuation_layer_ids.stock_move_id
                stock_moves = stock_moves[0] if stock_moves else False
                if stock_moves and stock_moves.picking_id:
                    link = stock_moves.picking_id._get_html_link()
                elif stock_moves and stock_moves.production_id:
                    link = stock_moves.production_id._get_html_link()
                elif stock_moves and stock_moves.raw_material_production_id:
                    link = stock_moves.raw_material_production_id._get_html_link()
                elif stock_moves:
                    link = stock_moves._get_html_link()
                if link:
                    move.message_post(body=f"Phân bổ giá trị hàng tồn kho đã được phân bổ cho phiếu này: {link}")
        return res
    
    def _build_credit_warning_message(self, record, updated_credit):
        if not record.partner_id.partner_group_id:
            res = super(AccountMove, self)._build_credit_warning_message(record, updated_credit)
        else:
            partner_id = record.partner_id.commercial_partner_id
            updated_credit -= partner_id.credit
            updated_credit += partner_id.partner_group_id.credit
            if not partner_id.partner_group_id.credit_limit or updated_credit <= partner_id.partner_group_id.credit_limit:
                return ''
            res = '%s đã đạt đến Hạn mức Tín dụng là : %s\nTổng số tiền phải trả '% (
                    partner_id.name,
                    formatLang(self.env, partner_id.partner_group_id.credit_limit, currency_obj=record.company_id.currency_id))
            if updated_credit > partner_id.partner_group_id.credit:
                res += '(bao gồm tài liệu này) '
            res += ': %s' % formatLang(self.env, updated_credit, currency_obj=record.company_id.currency_id)
        partner_id = record.partner_id.commercial_partner_id
        company_id = self.env.company
        if res and company_id.account_use_credit_limit and partner_id.is_prevent_over_credit:
            res = 'Khách hàng này bị chặn hoạt động\n' + res
        return res

    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        res = super(AccountMove, self)._compute_tax_totals()
        for move in self.sudo():
            tax_totals = move.tax_totals
            if tax_totals:
                amount = sum([line.price_subtotal for line in move.invoice_line_ids])
                tax_totals['amount_untaxed'] = amount
                tax_totals['formatted_amount_untaxed'] = move.currency_id.format(amount)
            move.tax_totals = tax_totals
        return res

    def action_copy_invoice_info(self):
        """Copy invoice_code, invoice_number, date_invoice từ dòng đầu tiên sang các dòng còn lại."""
        for move in self:
            lines = move.line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
            if not lines:
                continue
            first_line = lines[0]
            vals = {}
            if hasattr(first_line, 'invoice_code') and first_line.invoice_code:
                vals['invoice_code'] = first_line.invoice_code
            if hasattr(first_line, 'invoice_number') and first_line.invoice_number:
                vals['invoice_number'] = first_line.invoice_number
            if hasattr(first_line, 'date_invoice') and first_line.date_invoice:
                vals['date_invoice'] = first_line.date_invoice
            if vals:
                other_lines = lines - first_line
                if other_lines:
                    other_lines.write(vals)
        return True

