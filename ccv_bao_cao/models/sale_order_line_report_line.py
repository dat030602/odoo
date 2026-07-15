from odoo import models, fields,api
import logging

_logger = logging.getLogger(__name__)

class BaoCaoDongDonHang(models.Model):
    _name = 'sale.order.line.report.line'
    _description = 'Báo cáo dòng đơn hàng'
    _order = "date_order desc"

    date_order = fields.Datetime(string="Ngày đặt hàng")
    name = fields.Char(string="Tên")
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    package_product_id = fields.Many2one('product.product', string="Bao bì", store=True, compute="_compute_package_product_id")
    order_name = fields.Char(string="Mã đơn hàng")
    qty = fields.Float(string="Số lượng đặt hàng")
    qty_done = fields.Float(string="Số lượng đã giao")
    uom_id = fields.Many2one('uom.uom', string="ĐVT", related="product_id.uom_id",store=True)
    amount = fields.Float(string="Doanh số")
    user_id = fields.Many2one('res.users', string="Nhân viên bán hàng")
    partner_id = fields.Many2one('res.partner', string="Đối tác")
    
    team_id = fields.Many2one('crm.team', string="Đơn vị kinh doanh", related="partner_id.team_id",store=True)
    state_id = fields.Many2one('res.country.state', string="Tỉnh/Thành phố", related="partner_id.state_id",store=True)
    district_id = fields.Many2one('res.country.district', string="Quận/Huyện", related="partner_id.district_id",store=True)

    report_id = fields.Many2one('sale.order.line.report', string="Báo cáo")

    @api.depends("product_id")
    def _compute_package_product_id(self):
        bom_env = self.env['mrp.bom'].sudo()
        for rec in self:
            product_env = self.env['product.product'].sudo()
            if rec.product_id:
                bom = bom_env.search([('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)]).mapped('bom_line_ids').mapped('product_id')
                if bom:
                    product_id = bom.filtered(lambda l: l.default_code and "BB." in l.default_code)
                    if product_id:
                        product_env = product_id[0]
            rec.package_product_id = product_env
