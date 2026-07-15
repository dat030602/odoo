from platform import machine
from odoo import models, fields, api
import logging
import requests
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import json

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    machine_id = fields.Many2one('npk.weighing.machine', string="Máy cân")
    npk_weighing_history_id = fields.Many2one('npk.weighing.history', string="Thông tin cân")
    weighing_ticket_name = fields.Char(related='npk_weighing_history_id.name', string="Số phiếu máy cân")
    odoo_ticket_name = fields.Char(related='npk_weighing_history_id.odoo_ticket_name', string="Số phiếu Odoo")
    weighing_total = fields.Float(related='npk_weighing_history_id.total', string="Tổng khối lượng (kg)")
    weighing_counter = fields.Integer(related='npk_weighing_history_id.counter', string="Số lượng bao cân")
    state_weighing = fields.Selection(string="Trạng thái cân", selection=
        [
            ('draft','Chưa cân'),
            ('running', 'Đang cân'),
            ('finished', 'Đã cân'),
            ('cancel', 'Hủy')
        ],
     compute='_compute_state_weighing', store=True)
    bag_number = fields.Integer(string="Số lượng bao", compute='_compute_bag_number', store=True)

    @api.onchange('bom_id.tag_ids', 'plan_mrp_line_id')
    def _onchange_product_id_tag_ids(self):
        for rec in self:
            if rec.bom_id.tag_ids:
                if rec.plan_mrp_line_id and rec.plan_mrp_line_id.picking_type_id:
                    machine = self.env['npk.weighing.machine'].search([('tag_ids','in', rec.plan_mrp_line_id.tag_ids.ids),('factory_id.picking_type_id','=', rec.plan_mrp_line_id.picking_type_id.id)], limit=1)
                else:
                    machine = self.env['npk.weighing.machine'].search([('tag_ids','in', rec.bom_id.tag_ids.ids),('factory_id.picking_type_id','=', rec.picking_type_id.id)], limit=1)
                rec.machine_id = machine.id

    @api.depends('npk_weighing_history_id.is_finished', 'npk_weighing_history_id.is_deleted')
    def _compute_state_weighing(self):
        for rec in self:
            if rec.npk_weighing_history_id:
                if rec.npk_weighing_history_id.is_finished:
                    rec.state_weighing = 'finished'
                elif rec.npk_weighing_history_id.is_deleted:
                    rec.state_weighing = 'cancel'
                else:
                    rec.state_weighing = 'running'
            else:
                rec.state_weighing = 'draft'

    @api.depends('product_uom_qty', 'product_uom_id', 'product_id', 'product_id.default_specification_id')
    def _compute_bag_number(self):
        for rec in self:
            quantity = rec.product_uom_qty
            bag_number = 0

            default_specification_id = rec.product_id.default_specification_id
            if default_specification_id:
                if default_specification_id.uom_type == 'reference':
                    if rec.product_uom_id and rec.product_uom_id.uom_type == 'smaller':
                        bag_number = quantity / rec.product_uom_id.factor
                    if rec.product_uom_id and rec.product_uom_id.uom_type == 'bigger':
                        bag_number = quantity * rec.product_uom_id.factor
                if default_specification_id.uom_type == 'smaller':
                    if rec.product_uom_id and rec.product_uom_id.uom_type == 'reference':
                        bag_number = quantity * default_specification_id.factor
                    if rec.product_uom_id and rec.product_uom_id.uom_type == 'bigger':
                        bag_number = (quantity / rec.product_uom_id.factor)*default_specification_id.factor
                if default_specification_id.uom_type == 'bigger':
                    if rec.product_uom_id and rec.product_uom_id.uom_type == 'reference':
                        bag_number = quantity / default_specification_id.factor
                    if rec.product_uom_id and rec.product_uom_id.uom_type == 'smaller':
                        bag_number = (quantity * rec.product_uom_id.factor)/default_specification_id.factor

            rec.bag_number = bag_number

    def action_post_npk(self):
        """Tạo bản ghi NPK weighing từ lệnh sản xuất và gửi lên API"""
        self.ensure_one()
        if not self.machine_id:
            raise ValidationError("Bạn chưa chọn cân !!!")
        if self.state_weighing == 'finished':
            raise ValidationError("Cân đã hoàn thành !!!")
        
        # 1. Tìm hoặc tạo bản ghi npk.weighing.history
        history = self.npk_weighing_history_id
        if not history:
            history = self.env['npk.weighing.history'].create({
                'production_id': self.id,
                'machine_id': self.machine_id.id,
                'plan_counter': self.bag_number,
            })
            history._compute_production_id()
            self.npk_weighing_history_id = history

        # 2. Thực hiện đẩy lên máy cân (hàm này đã có logic kiểm tra tránh tạo trùng bên trong)
        history._create_weighing_ticket()

        now = fields.Datetime.now() + timedelta(hours=7)
        self.message_post(body="Đã đẩy/đồng bộ lên cân thành công vào lúc %s !!!" % now.strftime('%Y-%m-%d %H:%M:%S'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thông báo',
                'message': "Đã đẩy/đồng bộ lên cân thành công !!!",
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_check_status_weighing(self):
        """Kiểm tra trạng thái cân"""
        self.ensure_one()
        if not self.machine_id:
            raise ValidationError("Bạn chưa chọn cân !!!")
        if not self.npk_weighing_history_id:
            raise ValidationError("Bạn chưa đẩy lên cân !!!")
        return self.npk_weighing_history_id.action_check_status_weighing()

