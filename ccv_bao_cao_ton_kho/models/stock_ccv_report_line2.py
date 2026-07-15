from odoo import models, fields,api
from odoo.exceptions import UserError
import datetime
import logging

_logger = logging.getLogger(__name__)

class StockReportLine2(models.Model):
    _name = "stock.ccv.report.line2"

    name = fields.Char(string="Tên")
    report_name = fields.Char(string="Tên biên bản kiểm kê")
    date = fields.Datetime("Thời điểm kiểm kê")
    location_id = fields.Many2one("stock.location", "Kho kiểm kê")
    user_ids = fields.Many2many('stock.ccv.report.participant', string="Người tham dự")
    line_ids = fields.One2many('stock.ccv.report.stock.quant', 'report_line_id')
    parent_id = fields.Many2one("stock.ccv.report", string="Báo cáo", domain=[('type','=','bien_ban_kiem_ke')])
    picking_ids = fields.Many2many("stock.picking", string="Kho kiểm kê")
    picking_count = fields.Integer(compute="_compute_picking_ids")
    description = fields.Char(string="Lý do kiểm kê")
    
    @api.depends("picking_ids")
    def _compute_picking_ids(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.onchange('location_id')
    def _onchange_location_id(self):
        for rec in self:
            rec.line_ids.location_dest_id = rec.location_id

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        for rec in self:
            if rec.parent_id.user_ids:
                rec.user_ids = rec.parent_id.user_ids

    def action_print_excel(self):
        data = self._prepare_value()
        return self.env.ref('ccv_bao_cao_ton_kho.bien_ban_kiem_ke_report').report_action(None, data=data)
        

    def action_print_pdf(self):
        return self.env.ref('ccv_bao_cao_ton_kho.ccv_bao_cao_ton_kho_bien_ban_kiem_ke_vat_tu_hang_hoa_report').report_action(self)

    def _prepare_value(self):
        stock_quantity              = sum(self.line_ids.mapped("quantity"))
        stock_inventory_quantity    = sum(self.line_ids.mapped("inventory_quantity"))
        stock_diff_quantity         = sum(self.line_ids.mapped("diff_quantity"))

        lines = []
        count = 1
        for data in self.line_ids:
            default_code        = data.default_code         if data.default_code        else ""
            product_id          = data.product_id.name      if data.product_id          else ""
            uom_id              = data.uom_id.name          if data.uom_id              else ""
            quantity            = data.quantity             if data.quantity            else 0
            inventory_quantity  = data.inventory_quantity   if data.inventory_quantity  else 0
            diff_quantity       = data.diff_quantity        if data.diff_quantity       else 0
            
            vals = {
                "no"                          : count,
                "default_code"                : default_code,
                "product_id"                  : product_id,
                "uom_id"                      : uom_id,
                "stock_quantity"              : round(quantity,3),
                "stock_inventory_quantity"    : round(inventory_quantity,3),
                "stock_diff_quantity"         : round(diff_quantity,3),
                "value_quantity"              : '',
                "value_inventory_quantity"    : '',
                "value_diff_quantity"         : '',
            }
            count += 1
            lines.append(vals)
        
        user_ids = [
            {
                'name': user_id.name,
                'job': user_id.job,
                'representative': user_id.representative,
            } for user_id in self.user_ids
        ]

        return {
            "sum": {
                "sum_stock_quantity"              : round(stock_quantity,3),
                "sum_stock_inventory_quantity"    : round(stock_inventory_quantity,3),
                "sum_stock_diff_quantity"         : round(stock_diff_quantity,3),
                "sum_value_quantity"              : "",
                "sum_value_inventory_quantity"    : "",
                "sum_value_diff_quantity"         : "",
            },
            "date": self.parent_id.convert_date((self.date+ datetime.timedelta(hours=7))),
            "datetime": self.parent_id.convert_hour((self.date+ datetime.timedelta(hours=7))),
            "user_ids": user_ids,
            "lines": lines,
            "description": self.description or '',
        }

    def _action_create_picking(self, line_ids, location_id, location_dest_id, body):
        pk = self.env['stock.picking'].create({
            'picking_type_id': location_id.warehouse_id.int_type_id.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'reason_output_input_stock': "Kiểm kê theo: %s" % self.name.title(),
            'move_ids': [(0,0,{
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'product_uom_qty': abs(line.diff_quantity),
            }) for line in line_ids]
        })
        self.picking_ids |= pk
        pk.message_post(body=body)
        return pk

    def action_create_picking(self):
        self.ensure_one()
        body = "Điều chuyển được tạo từ %s" % self._get_html_link()
        line_ids = self.line_ids.filtered(lambda l:l.diff_quantity < 0)
        for location_id in line_ids.mapped('location_id'):
            for location_dest_id in line_ids.mapped('location_dest_id'):
                self._action_create_picking(line_ids,location_id,location_dest_id,body)
        line_ids = self.line_ids.filtered(lambda l:l.diff_quantity > 0)
        for location_id in line_ids.mapped('location_id'):
            for location_dest_id in line_ids.mapped('location_dest_id'):
                self._action_create_picking(line_ids,location_dest_id,location_id,body)

    def action_view_pk(self):
        self.ensure_one()
        lines = self.picking_ids
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        if len(lines) > 1:
            action['domain'] = [('id', 'in', lines.ids)]
        elif len(lines) == 1:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = lines.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
