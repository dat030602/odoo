from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    cur_location_stock_quant = fields.Float(string="Tồn kho Từ", compute="_compute_cur_stock_quant")
    cur_location_dest_stock_quant = fields.Float(string="Tồn kho Đến", compute="_compute_cur_stock_quant")
    # Ảnh sản phẩm
    product_image_512 = fields.Image(
        string="Ảnh bao bì",
        compute="_compute_product_image_512",
        inverse="_inverse_product_image_512",
        store=True,
        max_width=512,
        max_height=512
    )

    product_image_128 = fields.Image(
        string="Ảnh bao bì",
        compute="_compute_product_image_128",
        inverse="_inverse_product_image_128",
        store=True,
        max_width=128,
        max_height=128
    )

    # Ảnh bao bì
    packaging_image_512 = fields.Image(
        string="Ảnh sản phẩm",
        compute="_compute_packaging_image_512",
        inverse="_inverse_packaging_image_512",
        store=True,
        max_width=512,
        max_height=512
    )

    packaging_image_128 = fields.Image(
        string="Ảnh sản phẩm",
        compute="_compute_packaging_image_128",
        inverse="_inverse_packaging_image_128",
        store=True,
        max_width=128,
        max_height=128
    )

    product_image_1920 = fields.Image(
        string="Ảnh sản phẩm",
        related="product_id.image_1920",
        readonly=True,
    )

    # Compute & Inverse cho product_image
    @api.depends('product_image')
    def _compute_product_image_512(self):
        for rec in self:
            rec.product_image_512 = rec.product_image

    def _inverse_product_image_512(self):
        for rec in self:
            rec.product_image = rec.product_image_512

    @api.depends('product_image')
    def _compute_product_image_128(self):
        for rec in self:
            rec.product_image_128 = rec.product_image

    def _inverse_product_image_128(self):
        for rec in self:
            rec.product_image = rec.product_image_128
            
    @api.depends('product_id')
    def compute_get_image(self):
        for record in self:
            product_image = None
            packaging_image = None
            if record.product_id:
                if record.product_id.image_1024:
                    product_image = record.product_id.image_1024
                if record.product_id.packaging_image:
                    packaging_image = record.product_id.packaging_image
            record.product_image = product_image
            record.packaging_image = packaging_image

    # Compute & Inverse cho packaging_image
    @api.depends('packaging_image')
    def _compute_packaging_image_512(self):
        for rec in self:
            rec.packaging_image_512 = rec.packaging_image

    def _inverse_packaging_image_512(self):
        for rec in self:
            rec.packaging_image = rec.packaging_image_512

    @api.depends('packaging_image')
    def _compute_packaging_image_128(self):
        for rec in self:
            rec.packaging_image_128 = rec.packaging_image

    def _inverse_packaging_image_128(self):
        for rec in self:
            rec.packaging_image = rec.packaging_image_128

    @api.depends("state", "date", "location_id", "location_dest_id")
    def _compute_cur_stock_quant(self):
        for rec in self:
            inventory_quantity, inventory_quantity_dest = 0, 0
            def calculate_stock(product_id,location_id, date):
                query = "SELECT function_get_location_stock(%s,%s, %s)"
                self.env.cr.execute(query, (product_id,location_id, date))
                result = self.env.cr.fetchone()
                return float(result[0]) if result else 0.0
            if rec.state == 'done':
                inventory_quantity = calculate_stock(rec.product_id.id,rec.location_id.id, rec.date)
                inventory_quantity_dest = calculate_stock(rec.product_id.id,rec.location_dest_id.id, rec.date)
            rec.cur_location_stock_quant = inventory_quantity
            rec.cur_location_dest_stock_quant = inventory_quantity_dest

    def action_open_reference(self):
        self.ensure_one()
        action = super(StockMove, self).action_open_reference()
        if not self.picking_id and not self.reference and not self.production_id:
            return action
        if self.picking_id:
            action = {
                'res_model': "stock.picking",
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': self.picking_id.id,
            }
        elif self.production_id:
            action = {
                'res_model': "mrp.production",
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': self.production_id.id,
            }
        elif self.reference:
            picking_env = self.env['stock.picking'].sudo()
            mrp_env = self.env['mrp.production'].sudo()
            picking_id = picking_env.search([('name','=',self.reference)])
            mrp_id = mrp_env.search([('name','=',self.reference)])
            if picking_id:
                action = {
                    'res_model': "stock.picking",
                    'type': 'ir.actions.act_window',
                    'views': [[False, "form"]],
                    'res_id': picking_id.id,
                }
            elif mrp_id:
                action = {
                    'res_model': "mrp.production",
                    'type': 'ir.actions.act_window',
                    'views': [[False, "form"]],
                    'res_id': mrp_id.id,
                }
        return action

    def _get_accounting_data_for_valuation(self):
        """ Ghi đè để ưu tiên lấy tài khoản hạch toán từ Địa điểm kho (Location) """
        journal_id, acc_src, acc_dest, acc_valuation = super(StockMove, self)._get_accounting_data_for_valuation()

        # Nếu địa điểm nguồn (Src) có cấu hình tài khoản xuất
        if self.location_id.valuation_out_account_id:
            acc_src = self.location_id.valuation_out_account_id.id

        # Nếu địa điểm đích (Dest) có cấu hình tài khoản nhập
        if self.location_dest_id.valuation_in_account_id:
            acc_dest = self.location_dest_id.valuation_in_account_id.id

        return journal_id, acc_src, acc_dest, acc_valuation