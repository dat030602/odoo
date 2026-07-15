from odoo import models, fields, api
import logging
from odoo.tools import image_process
import base64

_logger = logging.getLogger(__name__)


class SaleOrderLinh(models.Model):
    _inherit = "sale.order.line"

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

