# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging
import re

_logger = logging.getLogger(__name__)

class SaleInvoicesListLine(models.Model):
    _name = 'sale.invoices.list.line.ccv'
    _description = 'Chi tiết bảng kê hóa đơn bán ra CCV'
    _order = 'invoice_code_key desc,invoice_code desc,invoice_number asc,date asc,move_id desc'
    
    parent_id = fields.Many2one('sale.invoices.list.ccv', ondelete='cascade')
    name = fields.Char('Mô tả dòng', compute='_compute_account_move_line', store=True)
    invoice_code_key = fields.Char('Ký hiệu mẫu HĐ', compute='_compute_account_move_line', store=True)
    invoice_code = fields.Char('Ký hiệu HĐ', compute='_compute_account_move_line', store=True)
    invoice_number = fields.Char('Số hoá đơn', compute='_compute_account_move_line', store=True)
    invoice_date = fields.Date('Ngày hoá đơn', compute='_compute_account_move_line', store=True)
    date = fields.Date('Ngày chứng từ', compute='_compute_account_move_line', store=True)
    ref = fields.Char('Số chứng từ', compute='_compute_account_move_line', store=True)
    buyer_id = fields.Many2one('res.partner', string='Người mua', compute='_compute_account_move_line', store=True)
    buyer_tax = fields.Char('Mã số thuế người mua', related='buyer_id.vat', store=True)
    product_id = fields.Many2one('product.product', string='Mặt hàng', compute='_compute_account_move_line', store=True)
    base_amount = fields.Monetary('Doanh số bán chưa có thuế GTGT', compute='_compute_account_move_line', store=True)
    tax_id = fields.Many2one('account.tax', string='Thuế suất', compute='_compute_account_move_line', store=True)
    tax_amount = fields.Monetary('Thuế GTGT', digits="Product Price", compute='_compute_account_move_line', store=True)
    tax_account_id = fields.Many2one('account.account', string='TK Thuế', compute='_compute_account_move_line', store=True)
    company_id = fields.Many2one('res.company', string='Công ty', related='parent_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', related='company_id.currency_id', store=True)
    aml_id = fields.Many2one('viettel.sinvoice.data', string='Dòng định khoản', store=True, ondelete='cascade')
    move_id = fields.Many2one('viettel.sinvoice', string='Phiếu định khoản', store=True)

    def action_view_account_move(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_journal_line').sudo().read()[0]
        if len(self) > 1:
            action['domain'] = [('id', 'in', self.move_id.invoice_id.ids)]
        else:
            action['res_id'] = self.move_id.invoice_id.id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
        return action

    @api.depends('move_id.sinvoice_line_ids.invoiceSeri', 'move_id.sinvoice_line_ids.templateCode', 'move_id.sinvoice_line_ids.invoiceNumber',
                 'aml_id.account_id', 'aml_id.product_id', 'aml_id.partner_vat_id', 'move_id.invoice_id', 'aml_id.tax_ids')
    def _compute_account_move_line(self):
        for line in self:
            aml_id = line.aml_id
            if not aml_id:
                continue
                
            move_id = aml_id.sinvoice_id
            line.move_id = move_id

            invoice_line = move_id.sinvoice_line_ids.sorted('invoiceIssuedDate', reverse=True)[0] if move_id.sinvoice_line_ids else move_id.sinvoice_line_ids
            
            
            line.invoice_code = invoice_line.invoiceSeri if invoice_line and invoice_line.invoiceSeri else move_id.config_id.vsi_series
            line.invoice_code_key = invoice_line.templateCode if invoice_line and invoice_line.templateCode else move_id.config_id.vsi_template
            line.invoice_number = invoice_line.invoiceNumber if invoice_line and invoice_line.invoiceNumber else (invoice_line.invoiceNo if invoice_line and invoice_line.invoiceNo else move_id.name)
            line.name = aml_id.name

            # Xử lý thuế
            sign = -1 if (aml_id.account_id and aml_id.account_id.code.startswith('521')) or move_id.type in ('out_refund', 'in_refund') else 1
            line.base_amount = aml_id.price_subtotal * sign
            line.date = move_id.invoice_id.date
            line.invoice_date = move_id.invoiceIssuedDate
            line.ref = move_id.invoice_id.name
            line.buyer_id = move_id.partner_vat_id
            line.product_id = aml_id.product_id
            line.tax_id = aml_id.tax_ids[0] if aml_id.tax_ids else False
            line.tax_amount = aml_id.price_tax * sign
            line.tax_account_id = aml_id.account_id
