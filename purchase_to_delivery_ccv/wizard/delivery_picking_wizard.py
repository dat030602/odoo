# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DeliveryPickingWizard(models.TransientModel):
    _name = 'delivery.picking.wizard'
    _description = 'Wizard to create deliveries by container and select operation type'

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
        required=True,
        help='Select the operation type for the delivery orders.'
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        readonly=True
    )

    def action_create_deliveries(self):
        self.ensure_one()
        return self.purchase_order_id.with_context(picking_type_id=self.picking_type_id.id).action_create_deliveries_by_container()
