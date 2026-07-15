from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class CreateMrpWizard(models.TransientModel):
    _name = 'create.mrp.wizard'
    _description = 'Create Picking Wizard'

    approval_request_id = fields.Many2one('approval.request', string="Đề xuất")
    picking_type_id = fields.Many2one('stock.picking.type', string="Loại hoạt động",domain="[('code','=','mrp_operation')]")
    scheduled_date = fields.Datetime(string="Ngày dùng tồn")
    line_ids = fields.One2many('create.mrp.line.wizard','parent_id',string="Chi tiết")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        approval_request_id = context.get('default_approval_request_id')
        res['scheduled_date'] = datetime.now()
        approval = self.env['approval.request'].browse(approval_request_id)
        res['approval_request_id'] = approval._origin.id if approval else False
        return res

    @api.onchange('approval_request_id')
    def _onchange_picking_id_approval_request_id(self):
        factory_default_ids = self.env['factory.product.default'].search([])
        for rec in self:
            rec.line_ids = [(5, 0, 0)]
            new_lines = []
            for line in rec.approval_request_id.product_line_ids.filtered(lambda l: l.qty_produced > 0):
                product_id = line.product_id
                picking_type_id = self.env['stock.picking.type']
                for factory_default_id in factory_default_ids:
                    cur_fac_pro = factory_default_id._get_factory_product(product_id)
                    if cur_fac_pro:
                        picking_type_id = cur_fac_pro.picking_type_id
                        break
                new_lines.append((0, 0, {
                    'name': rec.approval_request_id.name,
                    'product_id': line.product_id._origin.id,
                    'quantity': line.qty_produced,
                    'product_uom': line.product_uom_id._origin.id,
                    'picking_type_id': picking_type_id.id,
                })) 
            rec.line_ids = new_lines
            rec.line_ids._onchange_product_id()
            
    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        for rec in self:
            rec.line_ids.picking_type_id = rec.picking_type_id
        
    def action_create_mrp_order(self):
        vals = []
        for line in self.line_ids.filtered(lambda l: l.bom_id and l.quantity > 0):
            partner_names = ', '.join(set(self.approval_request_id.mapped('sale_ids').mapped('partner_id').mapped('name')))
            sale_names = ', '.join(self.approval_request_id.mapped('sale_ids').mapped('name'))
            description = self.approval_request_id.description or ''

            vals.append({
                'product_id': line.product_id.id,
                'bom_id': line.bom_id.id if line.bom_id else False,
                'date_planned_start': self.scheduled_date,
                'picking_type_id': line.picking_type_id.id,
                'user_id': line.picking_type_id.user_id.id if line.picking_type_id.user_id else False,
                'stock_date_receipt': self.scheduled_date,
                'product_qty': line.quantity,
                'interpretation': '%s\n%s\n%s\n%s' % (self.approval_request_id.name, partner_names, sale_names, description),
                'origin': '%s - %s - %s - %s' % (self.approval_request_id.name, partner_names, sale_names, description),
                'sale_ids': [(4,sale_id.id) for sale_id in self.approval_request_id.mapped('sale_ids')],
                'partner_ids': [(4,partner_id.id) for partner_id in self.approval_request_id.mapped('sale_ids').mapped('partner_id')],
            })
        mrp_ids = self.env['mrp.production'].create(vals)
        mrp_ids._onchange_product_id_tag_ids()
        for mrp_id in mrp_ids:
            if mrp_id.machine_id:
                mrp_id.action_post_npk()
            body = "Lệnh sản xuất được tạo từ %s" % self.approval_request_id._get_html_link()
            mrp_id.message_post(body=body)
            body = "Lệnh sản xuất được tạo: %s" % mrp_id._get_html_link()
            self.approval_request_id.message_post(body=body)