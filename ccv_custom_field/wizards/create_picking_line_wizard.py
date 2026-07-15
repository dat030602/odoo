from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

class CreatePickingLineWizard(models.TransientModel):
    _name = 'create.picking.line.wizard'
    _description = 'Create Picking Wizard'

    name = fields.Char(string="Mô tả")
    parent_id = fields.Many2one('create.picking.wizard', required=True)
    partner_id = fields.Many2one('res.partner', string="Liên hệ", required=True)
    product_id = fields.Many2one('product.product', string="Sản phẩm", required=True)
    quantity = fields.Float(string="Số lượng", digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', string="ĐVT")
    picking_type_id = fields.Many2one('stock.picking.type', string="Loại hoạt động")
