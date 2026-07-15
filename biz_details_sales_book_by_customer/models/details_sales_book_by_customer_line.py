# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date

class DetailsSalesBookByCustomerLine(models.Model):
    _name = 'details.sales.book.by.customer.line'
    _description = 'Sổ chi tiết bán hàng theo khách hàng'
    _order = 'sm_date,sm_write_date,sm_partner_id'

    # To sort
    sm_date = fields.Datetime('SM: Ngày chứng từ', related='picking_id.stock_date_receipt', store=True)
    sm_write_date = fields.Datetime('SM: Ngày chứng từ', related='picking_id.write_date', store=True)
    sm_partner_id = fields.Many2one('res.partner', string='SM: Khách hàng', related='picking_id.partner_id', store=True)

    parent_id = fields.Many2one('details.sales.book.by.customer', string='Sổ chi tiết bán hàng theo khách hàng')

    reference = fields.Char('Số chứng từ')
    date = fields.Date('Ngày chứng từ')
    vat_sinvoice_number = fields.Char('Số hoá đơn')
    vat_sinvoice_date = fields.Date('Ngày hoá đơn')
    picking_id = fields.Many2one('stock.picking', string='Phiếu xuất kho')
    stock_sale_export = fields.Char('Diễn giải chung')
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    product_uom = fields.Many2one('uom.uom', string='ĐVT', related='product_id.uom_id', store=True)
    qty_invoiced = fields.Float('Tổng số lượng bán', digits='Product Unit of Measure')
    price_unit = fields.Monetary('Đơn giá')
    price_subtotal = fields.Monetary('Doanh số chưa thuế')
    amount_tax = fields.Monetary('Giá trị thuế')
    price_subtotal_tax = fields.Monetary('Doanh số sau thuế')
    qty_done = fields.Float('Số lượng trả lại', digits='Product Unit of Measure')
    price_done = fields.Monetary('Giá trị trả lại')
    sale_line_id = fields.Many2one('sale.order.line', string='Dòng đơn hàng')
    user_id = fields.Many2one('res.users', string='NV bán hàng', related='order_id.user_id', store=True)
    partner_ward_district = fields.Char(string='Xã/Phường', compute='_compute_partner_ward_district', store=True)
    order_state_id = fields.Many2one('res.country.state', string='Tỉnh/Thành phố', related='order_id.order_state_id', store=True)
    order_id = fields.Many2one('sale.order', string='Đơn hàng', related='sale_line_id.order_id', store=True)
    team_id = fields.Many2one('crm.team', string='Khu vực', related='order_id.team_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Đơn vị tiền tệ', related='order_id.currency_id', store=True)

    @api.depends('partner_id', 'partner_id.wards_id', 'partner_id.district_id')
    def _compute_partner_ward_district(self):
        for rec in self:
            res = []
            if rec.partner_id and rec.partner_id.wards_id:
                res.append(rec.partner_id.wards_id.name)
            if rec.partner_id and rec.partner_id.district_id:
                res.append(rec.partner_id.district_id.name)
            rec.partner_ward_district = " - ".join(res) if res else ""
