# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging
import re

_logger = logging.getLogger(__name__)

class PurchaseInvoicesListLine(models.Model):
    _name = 'purchase.invoices.list.line.ccv'
    _description = 'Chi tiết bảng kê hóa đơn mua vào CCV'
    _order = 'invoice_code_key desc,invoice_code desc,invoice_number asc,date asc,move_id desc'
    
    parent_id = fields.Many2one('purchase.invoices.list.ccv', ondelete='cascade')
    invoice_code_key = fields.Char('Ký hiệu mẫu HĐ', compute='_compute_account_move_line', store=True)
    invoice_code = fields.Char('Ký hiệu HĐ', compute='_compute_account_move_line', store=True)
    invoice_number = fields.Char('Số hoá đơn', compute='_compute_account_move_line', store=True)
    invoice_date = fields.Date('Ngày hoá đơn', compute='_compute_account_move_line', store=True)
    date = fields.Date('Ngày chứng từ', compute='_compute_account_move_line', store=True)
    ref = fields.Char('Số chứng từ', compute='_compute_account_move_line', store=True)
    seller_id = fields.Many2one('res.partner', string='Người bán', compute='_compute_account_move_line', store=True)
    seller_tax = fields.Char('Mã số thuế người bán', related='seller_id.vat', store=True)
    product_id = fields.Many2one('product.product', string='Mặt hàng', compute='_compute_account_move_line', store=True)
    base_amount = fields.Monetary('Giá trị', compute='_compute_account_move_line', store=True)
    tax_id = fields.Many2one('account.tax', string='Thuế suất', compute='_compute_account_move_line', store=True)
    tax_amount = fields.Monetary('Thuế GTGT', digits="Product Price", compute='_compute_account_move_line', store=True)
    tax_account_id = fields.Many2one('account.account', string='TK Thuế', compute='_compute_account_move_line', store=True)
    company_id = fields.Many2one('res.company', string='Công ty', related='parent_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', related='company_id.currency_id', store=True)
    aml_id = fields.Many2one('account.move.line', string='Dòng định khoản', store=True, ondelete='cascade')
    move_id = fields.Many2one('account.move', string='Phiếu định khoản', store=True)
    is_not_uploaded = fields.Boolean('Không đẩy', default=False)

    def action_view_account_move(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_journal_line').sudo().read()[0]
        if len(self) > 1:
            action['domain'] = [('id', 'in', self.mapped('move_id.id'))]
        else:
            action['res_id'] = self.aml_id.move_id.id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
        return action

    @api.depends('aml_id.invoice_code', 'aml_id.invoice_number', 'aml_id.account_id', 'aml_id.product_id', 'aml_id.partner_id', 'aml_id.move_id')
    def _compute_account_move_line(self):
        for line in self:
            aml_id = line.aml_id
            move_id = aml_id.move_id
            line.move_id = move_id
            line.invoice_code = aml_id.invoice_number.split('/')[0] if aml_id.invoice_number and '/' in aml_id.invoice_number else ''
            
            # Xử lý invoice_code_key và invoice_code từ aml_id.invoice_code
            if aml_id.invoice_code:
                # Nếu ký tự đầu là số thì lấy số đó
                if aml_id.invoice_code[0].isdigit():
                    # Extract số từ đầu chuỗi
                    match = re.match(r'^\d+', aml_id.invoice_code)
                    if match:
                        line.invoice_code = match.group(0)
                        # Cập nhật invoice_code_key với phần còn lại (sau số)
                        remaining = aml_id.invoice_code[match.end():]
                        line.invoice_code_key = remaining if remaining else ''
                    else:
                        line.invoice_code_key = aml_id.invoice_code
                else:
                    # Nếu không bắt đầu bằng số, giữ nguyên
                    line.invoice_code_key = aml_id.invoice_code
            else:
                line.invoice_code_key = ''
            
            line.invoice_number = aml_id.invoice_number.split('/')[1] if aml_id.invoice_number and '/' in aml_id.invoice_number else aml_id.invoice_number

            line.tax_id = aml_id.tax_ids[0] if aml_id.tax_ids else False
            line.tax_account_id = aml_id.account_id
            if move_id.move_type != 'entry':
                line.base_amount = abs(aml_id.balance)
                taxes = aml_id.tax_ids.compute_all(
                    price_unit=abs(aml_id.balance),
                    quantity=1,
                    currency=aml_id.company_currency_id,
                    product=aml_id.product_id,
                    partner=aml_id.partner_id,
                )
                tax_amount = taxes['total_included'] - taxes['total_excluded']
                amount_tolerance = 50
                if move_id.currency_id != move_id.company_currency_id:
                    amount_tolerance = 200
                line_tax = move_id.line_ids.filtered(lambda l: l.tax_line_id in aml_id.tax_ids and abs(l.balance) >= tax_amount - amount_tolerance and abs(l.balance) <= tax_amount + amount_tolerance)
                if line_tax:
                    line.tax_amount = abs(sum(line_tax.mapped('balance')))
                else:
                    if move_id.currency_id == move_id.company_currency_id:
                        line.tax_amount = aml_id.tax_amount_value
                    else:
                        line.tax_amount = tax_amount
            else:
                line.base_amount = 0
                line.tax_amount = abs(aml_id.balance)
            line.date = move_id.date
            line.invoice_date = aml_id.date_invoice or move_id.invoice_date
            line.ref = move_id.name
            line.seller_id = aml_id.partner_id
            line.product_id = aml_id.product_id
