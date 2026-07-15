import ast
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    consignment_location_id = fields.Many2one('stock.location', string='Vị trí kho ký gửi', readonly=True, copy=False)
    finished_stock_qty = fields.Float(
        string='SL kho thành phẩm',
        compute='_compute_location_quantities',
        digits='Product Unit of Measure',
    )
    consignment_stock_qty = fields.Float(
        string='SL kho ký gửi',
        compute='_compute_location_quantities',
        digits='Product Unit of Measure',
    )

    @api.depends('move_finished_ids', 'move_finished_ids.state',
                 'move_finished_ids.location_dest_id', 'consignment_location_id')
    def _compute_location_quantities(self):
        for production in self:
            finished_qty = 0.0
            consignment_qty = 0.0
            for move in production.move_finished_ids.filtered(
                lambda m: m.product_id == production.product_id and m.state == 'done'
            ):
                if production.consignment_location_id and move.location_dest_id == production.consignment_location_id:
                    consignment_qty += move.product_uom_qty
                else:
                    finished_qty += move.product_uom_qty
            production.finished_stock_qty = finished_qty
            production.consignment_stock_qty = consignment_qty

    def action_open_consignment_wizard(self):
        self.ensure_one()
        return {
            'name': 'Chuyển Kho Ký gửi',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production.consignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_ids': self.ids,
            }
        }

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        res = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id, bom_line)
        
        source_location = self.location_src_id
        env_params = self.env['ir.config_parameter'].sudo()
        except_routes = ast.literal_eval(env_params.get_param('ccv_custom_mrp.except_routes', '[]'))
        locations = ast.literal_eval(env_params.get_param('ccv_custom_mrp.locations', '[]'))
        ktp_ids = ast.literal_eval(env_params.get_param('ccv_custom_mrp.ktp_ids', '[]'))
        bb_id = int(env_params.get_param('ccv_custom_mrp.bb_id', 0))
        
        # Lấy tất cả location từ tuyến cung ứng
        rule_ids = product_id.route_ids.filtered(lambda l: l.id not in except_routes).mapped('rule_ids')
        location_ids = rule_ids.mapped('location_src_id') + rule_ids.mapped('location_dest_id')
        
        bb = location_ids.filtered(lambda l: l.id == bb_id)  # Kho bao bì (BB)
        ot = location_ids.filtered(lambda l: l.id in locations)  # Kho thuộc danh sách cho phép
        
        def get_stock(location_id):
            return product_id.with_context(location=location_id).qty_available
        
        if bb:
            if get_stock(bb_id) > 0:
                source_location = bb[0]
            else:
                for ktp_id in ktp_ids:
                    if get_stock(ktp_id) > 0:
                        source_location = self.env['stock.location'].browse(ktp_id)
                        break
                else:
                    if not(get_stock(source_location.id) > 0):
                        for loc_id in locations:
                            if get_stock(loc_id) > 0:
                                source_location = self.env['stock.location'].browse(loc_id)
                                break
        elif ot:
            if source_location in ot:
                if not(get_stock(source_location.id) > 0):
                    for loc_id in ktp_ids:
                        if get_stock(loc_id) > 0:
                            source_location = self.env['stock.location'].browse(loc_id)
                            break
                    else:
                        for loc_id in locations:
                            if get_stock(loc_id) > 0:
                                source_location = self.env['stock.location'].browse(loc_id)
                                break
            else:
                for loc_id in ot:
                    if get_stock(loc_id.id) > 0:
                        source_location = loc_id
                        break
        
        res.update({"location_id": source_location.id, "warehouse_id": source_location.warehouse_id.id})
        return res


    @api.onchange('product_id', 'move_raw_ids')
    def _onchange_product_id(self):
        pass
    
    def write(self, vals):
        res = super(MrpProduction, self).write(vals)
        if 'picking_type_id' in vals:
            for rec in self:
                if rec.picking_type_id.warehouse_id.code not in rec.name:
                    rec.name = rec.picking_type_id.sequence_id.get_by_id()
        return res

    def _get_component_lines_over_limit(self):
        self.ensure_one()
        lines = []
        stock_date_receipt = self.stock_date_receipt
        for rec in self.move_raw_ids:
            qty_available = rec.product_id.with_context(
                to_date=stock_date_receipt.strftime("%Y-%m-%d 23:59:59"),
                location=rec.location_id.id,
            ).qty_available
            product_min_qty = self.env["stock.warehouse.orderpoint"].search(
                [("product_id", "=", rec.product_id.id),("location_id", "=", rec.location_id.id)]
            , limit=1).product_min_qty
            if product_min_qty and product_min_qty > qty_available:
                lines.append((rec.product_id.display_name, qty_available, product_min_qty, rec.product_uom.name))
        return lines

    def create_activity_mrp_production(self):
        for rec in self:
            lines = self._get_component_lines_over_limit()
            if not lines:
                continue
            lines_str = "<br/>".join([f"{line[0]}: Còn {line[1]}/{line[2]} {line[3]}" for line in lines])
            followers = rec.message_partner_ids.user_ids
            for follower in followers:
                activity_values = {
                    "res_model_id": self.env.ref("ccv_custom_mrp.model_mrp_production").id,
                    "res_id": rec.id,
                    "activity_type_id": self.env.ref("ccv_custom_mrp.mail_activity_data_warning_stock").id,
                    "user_id": follower.id,
                    "summary": "Cảnh báo tồn kho",
                    "note": f"""<strong>Cảnh báo tồn kho cho sản phẩm:</strong><br/>
                        {lines_str}""",
                }
                self.env["mail.activity"].create(activity_values)
    
    def button_mark_done(self):
        res = super(MrpProduction, self.sudo()).button_mark_done()
        self.create_activity_mrp_production()
        return res

    def action_view_account_moves(self):
        self.ensure_one()
        action_data = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action_data['domain'] = [('id', 'in', (self.move_raw_ids + self.move_finished_ids).mapped('account_move_ids').ids)]
        return action_data
