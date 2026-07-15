from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ccv_sale_plan_export_line(models.Model):
    _name = 'ccv.sale.plan.export.line'
    _inherit = ["ccv.sale.plan.export.line.mixin"]
    
    plan_export_id = fields.Many2one('ccv.sale.plan.export')
    parent_state = fields.Selection(string="Loại", selection=[
        ('draft','Nháp'),
        ('confirm','Xác nhận'),
        ('locked','Khóa'),
    ], related="plan_export_id.state")
    secondary_label_id = fields.Many2one('ccv.secondary.label', string="In tem phụ")
    qty_cur_delivered = fields.Float(string="Đã giao trong ngày", compute="_compute_qty_delivered")
    qty_out = fields.Float(string="Số lượng rớt")
    is_push_out = fields.Boolean(string="Đã đẩy rớt", default=False)

    

    @api.depends('plan_export_id', 'order_id', 'product_id')
    def _compute_qty_delivered(self):
        for rec in self:
            picking_ids = self.env['stock.picking'].search([('plan_sale_id', '=', rec.plan_export_id.id),('state', '=', 'done')]) \
                .filtered(lambda picking: picking.sale_id == rec.order_id)
            move_ids = picking_ids.move_ids.filtered(lambda move: move.product_id == rec.product_id)
            rec.qty_cur_delivered = sum(move_ids.mapped('quantity_done'))

    @api.constrains('qty_out', 'qty_delivery', 'product_uom_qty')
    def _constrains_qty_out(self):
        for rec in self:
            if rec.qty_out < 0:
                raise UserError(_("Số lượng rớt không được âm !!!"))
            if rec.qty_out > rec.qty_delivery:
                raise UserError(_("Số lượng rớt không được lớn hơn số lượng giao !!!"))
            if rec.qty_out > rec.product_uom_qty:
                raise UserError(_("Số lượng rớt không được lớn hơn số lượng đặt hàng !!!"))

    def _apply_qty_out_to_pickings(self):
        for rec in self:
            if not rec.plan_export_id or not rec.order_id or not rec.product_id:
                continue
            picking_ids = self.env['stock.picking'].search([
                ('plan_sale_id', '=', rec.plan_export_id.id),
                ('state', 'not in', ['done', 'cancel']),
                ('sale_id', '=', rec.order_id.id),
            ])
            if not picking_ids:
                continue
            qty_to_write = rec.qty_delivery - rec.qty_out
            picking_ids.action_reset_to_draft()
            move_ids = picking_ids.move_ids.filtered(lambda move: move.product_id == rec.product_id and move.product_uom_qty != qty_to_write)
            for move in move_ids:
                move.write({
                    'quantity_done': 0,
                    'product_uom_qty': qty_to_write,
                })

    def action_push_qty_out(self):
        self.ensure_one()
        self = self.sudo()
        line_ids = self.plan_export_id.line_ids.filtered(lambda line: line.qty_out > 0 and not line.is_push_out and self.team_id == line.team_id)
        team_ids = line_ids.mapped('team_id')
        for team in team_ids:
            lines = line_ids.filtered(lambda line: line.team_id == team).sorted('order_id')
            lines._constrains_qty_out()
            lines._apply_qty_out_to_pickings()

            channel = self.plan_export_id.channel_id
            if channel:
                lines_text = "<br/>".join([
                    "%(index)d.  %(order_name)s - %(product)s: %(qty)s %(uom)s" % {
                        'index': i + 1,
                        'order_name': line.order_id.name or '',
                        'product': line.product_id.display_name,
                        'qty': line.qty_out,
                        'uom': line.product_uom_id.name or '',
                    }
                     for i, line in enumerate(lines)])
                lines_vehicle = self.env['sale.vehicle.in.out.line'].search([
                    ('sale_vehicle_id.date', '=', self.plan_export_id.date),
                    ('sale_order_ids', 'in', lines.order_id.ids),
                ], limit=1)
                for line_vehicle in lines_vehicle:
                    vehicle_number = line_vehicle.vehicle_num or ''
                    vehicle_driver = line_vehicle.vehicle_driver or ''
                    message = ""
                    if vehicle_number or vehicle_driver:
                        if vehicle_number:
                            message = "Xe %s" % vehicle_number
                            if vehicle_driver and vehicle_driver != 'False':
                                message += " - Tài xế %s" % vehicle_driver
                    message = "%(message)s<br/>%(team)s xác nhận rớt đơn hàng: %(qty)s tấn<br/>%(product)s" % {
                        'message': message,
                        'team': team.name or '',
                        'product': lines_text,
                        'qty': sum(lines.mapped('qty_out')),
                    }
                    channel.message_post(body=message, message_type='comment')

            lines.is_push_out = True
        return True

    # delivery_date = fields.Date(string="Ngày giao hàng")
    # stock_date = fields.Date(string="Ngày dùng tồn", compute="")

    # @api.depends('delivery_date','plan_export_id.date')
    # def _compute_stock_date(self):
    #     for rec in self:
    #         rec.stock_date = rec.delivery_date if rec.delivery_date else (rec.plan_export_id.date if rec.plan_export_id.date else False)

    @api.model
    def default_get(self, fields_list):
        defaults = super(ccv_sale_plan_export_line, self).default_get(fields_list)
        label_id = self.env['ccv.secondary.label'].sudo().search([('is_default','=',True)], limit=1)
        defaults.update({'secondary_label_id': label_id.id if label_id else False,})
        return defaults
