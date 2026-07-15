from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

class CreatePickingLineWizard(models.TransientModel):
    _name = 'create.mrp.line.wizard'
    _description = 'Create Picking Wizard'

    name = fields.Char(string="Mô tả")
    parent_id = fields.Many2one('create.mrp.wizard', required=True)
    bom_id = fields.Many2one('mrp.bom', string="Định mức nguyên liệu", required=True)
    product_id = fields.Many2one('product.product', string="Sản phẩm", required=True)
    quantity = fields.Float(string="Số lượng", digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', string="ĐVT")
    picking_type_id = fields.Many2one('stock.picking.type', string="Loại hoạt động",domain="[('code','=','mrp_operation')]")
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        factory_default_ids = self.env['factory.product.default'].search([])
        for rec in self:
            product_id = rec.product_id
            boms_by_product = self.env['mrp.bom'].with_context(active_test=True)._bom_find(product_id, company_id=1, bom_type='normal')
            bom = boms_by_product[product_id]
            rec.bom_id = bom
            
            for factory_default_id in factory_default_ids:
                cur_fac_pro = factory_default_id._get_factory_product(product_id)
                if cur_fac_pro:
                    rec.picking_type_id = cur_fac_pro.picking_type_id.id
                    break
