# -*- coding: utf-8 -*-
from odoo import fields, models


class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    dsk_purchase_book_id = fields.Many2one('details.purchase.book', string='Sổ chi tiết mua hàng')
    details_internal_tf_book_id = fields.Many2one('details.internal.tf.book', string='Sổ nhập hàng tại cảng')
    details_stock_order_book_id = fields.Many2one('details.stock.order.book', string='Báo cáo hàng tồn kho khu vực')
    details_accounts_payable_book_id = fields.Many2one('details.accounts.payable.book', string='Báo cáo chi tiết công nợ phải trả')
    summary_accounts_payable_book_id = fields.Many2one('summary.accounts.payable.book', string='Báo cáo tổng hợp công nợ phải trả')
