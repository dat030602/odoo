from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class RemoveInternalPickingMrpWizard(models.TransientModel):
    _name = 'remove.internal.picking.mrp.wizard'
    _description = 'Remove Internal Picking MRP Wizard'

    mrp_production_ids = fields.Many2many('mrp.production', string="Phiếu sản xuất")
    picking_type_id = fields.Many2one('stock.picking.type', string="Loại hoạt động", required=True)
    location_src_id = fields.Many2one('stock.location', string="Vị trí nguyên liệu", required=True)
    location_dest_id = fields.Many2one('stock.location', string="Vị trí Thành phẩm", required=True)

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['picking_type_id'] = self.env.context.get('default_picking_type_id')
        return res

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        if self.picking_type_id:
            self.location_src_id = self.picking_type_id.default_location_src_id
            self.location_dest_id = self.picking_type_id.default_location_dest_id

    def action_confirm(self):
        for rec in self:
            rec.mrp_production_ids.action_remove_internal_picking(rec.location_src_id, rec.location_dest_id)

