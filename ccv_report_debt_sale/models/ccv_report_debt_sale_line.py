from odoo import api, fields, models, _
import datetime
from odoo.exceptions import ValidationError

class CcvReportDebtSaleLine(models.Model):
    _name = 'ccv.report.debt.sale.line'
    _description = 'Chi tiết sổ tổng hợp bán hàng'
    _order = 'parent_id, team_id, partner_id, sequence'

    parent_id = fields.Many2one('ccv.report.debt.sale', string='Sổ tổng hợp bán hàng')
    sequence = fields.Integer(string='Số thứ tự', default=1)

    aml_id = fields.Many2one('account.move.line', string='Dòng Hoá đơn')
    move_id = fields.Many2one('account.move', string='Hoá đơn', related="aml_id.move_id", store=True)
    name = fields.Char('Số chứng từ', related="move_id.name", store=True)


    date = fields.Date('Ngày chứng từ', compute="_compute_aml", store=True)
    vat_sinvoice_number = fields.Char('Số hoá đơn', compute="_compute_aml", store=True)
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    product_id = fields.Many2one('product.product', string='Sản phẩm', compute="_compute_aml", store=True)
    product_uom = fields.Many2one('uom.uom', string='ĐVT', compute="_compute_aml", store=True)
    product_name = fields.Char('Tên sản phẩm', compute="_compute_aml", store=True)
    @api.depends('aml_id.product_id', 'aml_id.name', 'move_id.date', 'move_id.vat_sinvoice_number', 'aml_id.product_uom_id', 'aml_id.quantity', 'aml_id.price_unit', 'aml_id.price_subtotal', 'aml_id.tax_amount_value', 'aml_id.price_total')
    def _compute_aml(self):
        for record in self:
            if record.aml_id:
                record.product_name = record.aml_id.product_id.name_get()[0][1] if record.aml_id.product_id else record.aml_id.name
            else:
                record.product_name = 'Đầu kỳ'
            sign = -1 if record.move_id.move_type == 'out_refund' else 1
            record.date = record.move_id.date
            record.vat_sinvoice_number = record.move_id.vat_sinvoice_number
            record.product_id = record.aml_id.product_id
            record.product_uom = record.aml_id.product_uom_id
            record.qty_invoiced = 0 if record.move_id.payment_id else (record.aml_id.quantity * sign)
            record.price_unit = record.aml_id.price_unit
            record.price_subtotal = record.aml_id.price_subtotal * sign
            record.amount_tax = record.aml_id.tax_amount_value * sign
            record.price_total = record.aml_id.price_total * sign


    # Bán hàng
    qty_invoiced = fields.Float('SL bán', digits='Product Unit of Measure', compute="_compute_aml", store=True)
    price_unit = fields.Float('Đơn giá', compute="_compute_aml", store=True)
    price_subtotal = fields.Monetary('DS chưa thuế', compute="_compute_aml", store=True)
    amount_tax = fields.Monetary('Thuế VAT', compute="_compute_aml", store=True)
    price_total = fields.Monetary('DS sau thuế', compute="_compute_aml", store=True)
    currency_id = fields.Many2one('res.currency', string='Đơn vị tiền tệ', related='move_id.currency_id', store=True)

    # Công nợ
    pre_line = fields.Many2one('ccv.report.debt.sale.line', string='Dòng trước')
    debt_in = fields.Monetary('Thu nợ', store=True, compute='_compute_debt_in')
    debt_end = fields.Monetary('Nợ cuối')
    @api.depends('aml_id.balance', 'move_id.payment_id')
    def _compute_debt_in(self):
        for record in self:
            record.debt_in = abs(record.aml_id.balance) if record.move_id.payment_id else 0.0
    
    user_id = fields.Many2one('res.users', string='NV bán hàng', compute='_compute_order_info', store=True)
    order_id = fields.Many2one('sale.order', string='Đơn hàng', compute='_compute_order_info', store=True)
    team_id = fields.Many2one('crm.team', string='Khu vực', compute='_compute_order_info', store=True)

    @api.depends('partner_id', 'aml_id.sale_line_ids.order_id', 'aml_id.sale_line_ids.order_id.user_id','aml_id.sale_line_ids.order_id.team_id', 'move_id.currency_id')
    def _compute_order_info(self):
        for record in self:
            order = record.aml_id.sale_line_ids.order_id
            record.user_id = order.user_id or record.partner_id.user_id
            record.order_id = order
            record.team_id = order.team_id or record.partner_id.team_id
            record.currency_id = record.move_id.currency_id or self.env.company.currency_id

    def action_view_move(self):
        move_id = self.move_id
        action = self.env.ref('account.action_move_journal_line').sudo().read()[0]
        if move_id.payment_id:
            action = self.env.ref('account.action_account_payments').sudo().read()[0]
            move_id = move_id.payment_id
        action['views'] = [(False, 'form')]
        action['res_id'] = move_id.id
        return action
