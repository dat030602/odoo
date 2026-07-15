from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class CreatePickingWizard(models.TransientModel):
    _name = 'create.picking.wizard'
    _description = 'Create Picking Wizard'

    approval_request_id = fields.Many2one('approval.request', string="Đề xuất")
    partner_id = fields.Many2one('res.partner', string="Liên hệ", required=True)
    picking_id = fields.Many2one('stock.picking', string="Phiếu kho")
    picking_type_id = fields.Many2one('stock.picking.type', string="Loại hoạt động")
    scheduled_date = fields.Datetime(string="Ngày dùng tồn")
    line_ids = fields.One2many('create.picking.line.wizard','parent_id',string="Chi tiết")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        approval_request_id = context.get('default_approval_request_id')
        picking_id = context.get('default_picking_id')
        res['scheduled_date'] = datetime.now()
        if approval_request_id:
            approval = self.env['approval.request'].browse(approval_request_id)
            res['approval_request_id'] = approval._origin.id if approval else False
            res['partner_id'] = approval.request_owner_id.partner_id._origin.id if approval.request_owner_id else False
        elif picking_id:
            picking_id = self.env['stock.picking'].browse(picking_id)
            res['picking_id'] = picking_id._origin.id if picking_id else False
            res['partner_id'] = picking_id.partner_id._origin.id if picking_id.partner_id else False
            if not res.get('picking_type_id'):
                res['picking_type_id'] = picking_id.picking_type_id._origin.id if picking_id.picking_type_id else False
        return res

    @api.onchange('picking_id','approval_request_id')
    def _onchange_picking_id_approval_request_id(self):
        for rec in self:
            rec.line_ids = [(5, 0, 0)]
            new_lines = []
            if rec.approval_request_id:
                for line in rec.approval_request_id.product_line_ids:
                    new_lines.append((0, 0, {
                        'name': rec.approval_request_id.name,
                        'partner_id': line.partner_id._origin.id if line.partner_id else rec.partner_id._origin.id,
                        'product_id': line.product_id._origin.id,
                        'quantity': line.quantity,
                        'product_uom': line.product_uom_id._origin.id,
                        'picking_type_id': line.picking_type_id._origin.id,
                    }))
                rec.line_ids = new_lines

            elif rec.picking_id:
                for line in rec.picking_id.move_ids:
                    new_lines.append((0, 0, {
                        'name': line.name,
                        'partner_id': rec.partner_id._origin.id,
                        'product_id': line.product_id._origin.id,
                        'quantity': line.quantity_done,
                        'product_uom': line.product_uom._origin.id,
                        'picking_type_id': rec.picking_type_id._origin.id,
                    }))
                rec.line_ids = new_lines
    
    @api.onchange('partner_id')
    def _onchange_partner_id_lines(self):
        for rec in self:
            if rec.line_ids:
                if rec.partner_id:
                    rec.line_ids.write({
                        'partner_id': rec.partner_id._origin.id
                    })

    def _action_create_picking_w_approval(self):
        self.ensure_one()
        approval = self.approval_request_id
        if not self.line_ids:
            raise UserError("Không có sản phẩm để tạo phiếu xuất !!!")
        reason = ""
        if approval.description:
            reason = approval.description
        elif approval.reason:
            reason = approval.reason
        elif approval.request_note_ids:
            reason = ', '.join(approval.request_note_ids.mapped('description'))

        picking_type_ids = self.line_ids.mapped('picking_type_id')
        partner_ids = self.line_ids.mapped('partner_id')
        for picking_type_id in picking_type_ids:
            for partner_id in partner_ids:
                picking = self._action_create_picking(partner_id,picking_type_id,approval.name,reason)
                if picking:
                    picking.message_post(body=f"Phiếu đề xuất {approval._get_html_link()}",)
                    # Gắn bản in PDF vào chatter của approval.request
                    
                    report_pdf = self.env['ir.actions.report']._render_qweb_pdf("ccv_custom_field.phieu_xuat_kho_vat_tu_report", picking._origin.id)
                    approval.message_post(
                        body=f"Phiếu kho {picking._get_html_link()}",
                        attachments=[(f'{picking.name}.pdf', report_pdf[0])],
                    )

    def _action_create_picking_w_picking(self):
        self.ensure_one()
        picking_id = self.picking_id
        if not self.line_ids:
            raise UserError("Không có sản phẩm để tạo phiếu xuất !!!")
        reason = ""
        if picking_id.reason_output_input_stock:
            reason = picking_id.reason_output_input_stock
        picking_type_ids = self.line_ids.mapped('picking_type_id')
        partner_ids = self.line_ids.mapped('partner_id')
        for picking_type_id in picking_type_ids:
            for partner_id in partner_ids:
                picking = self._action_create_picking(partner_id,picking_type_id,picking_id.name,reason)
                if picking:
                    picking_id.message_post(body=f"Phiếu kho chuyển tiếp {picking._get_html_link()}",)
                    picking.message_post(body=f"Phiếu kho nguồn {picking_id._get_html_link()}",)

    def _action_create_picking(self,partner_id,picking_type_id,name,reason):
        self.ensure_one()
        driver_consignee_id = self.env['res.users'].search([('partner_id','=',partner_id._origin.id)],limit=1)
        picking_vals = {
            'partner_id': partner_id._origin.id,
            'picking_type_id': picking_type_id._origin.id,
            'scheduled_date': self.scheduled_date,
            'stock_date_receipt': self.scheduled_date,
            'origin': name,
            'reason_output_input_stock': reason,
            'driver_consignee_id': driver_consignee_id._origin.id if driver_consignee_id else self.approval_request_id.request_owner_id._origin.id,
        }
        picking = self.env['stock.picking'].create(picking_vals)
        # Tạo stock.move từ dòng sản phẩm của đề xuất
        line_ids = self.line_ids.filtered(lambda l:l.partner_id == partner_id and l.picking_type_id == picking_type_id)
        if not line_ids:
            return False
        for line in line_ids:
            if not line.product_id or not line.quantity:
                continue
            self.env['stock.move'].create({
                'product_id': line.product_id._origin.id,
                'name': line.name if line.name else line.product_id.name,
                'product_uom_qty': line.quantity,
                'quantity_done': line.quantity,
                'product_uom': line.product_uom._origin.id,
                'picking_id': picking._origin.id,
                'location_id': picking_type_id._origin.default_location_src_id._origin.id,
                'location_dest_id': picking_type_id._origin.default_location_dest_id._origin.id,
            })
        picking.action_confirm()
        if picking.state != 'done':
            picking.with_context(skip_immediate=True, manual_validate_date_time=picking.stock_date_receipt).button_validate()
        return picking

    def action_create_picking(self):
        self.ensure_one()
        if self.approval_request_id:
            self._action_create_picking_w_approval()
        elif self.picking_id:
            self._action_create_picking_w_picking()
        
