from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class FactoryProductDefault(models.Model):
    _name = 'factory.product.default'

    name = fields.Char(compute="_compute_name_factory")
    picking_type_id = fields.Many2one("stock.picking.type", string="Nhà máy", domain=[("code", "=", "mrp_operation")])
    product_ids = fields.Many2many('product.product')

    @api.depends('picking_type_id.factory_name')
    def _compute_name_factory(self):
        for rec in self:
            if rec.picking_type_id and rec.picking_type_id.factory_name:
                rec.name = rec.picking_type_id.factory_name
            else:
                rec.name = "Nhà máy"

    def _get_factory_product(self, product_id):
        self.ensure_one()
        if product_id and self.product_ids.filtered(lambda l: l == product_id):
            return self
        return False
