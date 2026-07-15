from odoo import models, fields,api
import logging
import ast
import datetime
import calendar

_logger = logging.getLogger(__name__)

class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    service_id = fields.Many2one('product.product', string="Dịch vụ", domain=[('detailed_type','=','service')])
    picking_type_id = fields.Many2one('stock.picking.type', string='Loại hoạt động')
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', default=False)
    partner_id = fields.Many2one('res.partner', string="Liên hệ")
    product_image = fields.Binary(string="Ảnh sản phẩm", related="product_id.image_1024")
    line_image = fields.Binary(string="Hình ảnh")
    qty_produced = fields.Float(string="Sản xuất",digits="Product Unit of Measure")
    qty_bb_used = fields.Float(string="SL BB đã sử dụng", digits="Product Unit of Measure")
    note = fields.Char(string="Ghi chú")
    mkt_comment = fields.Char(string="Ý kiến MKT")
    qty_available = fields.Float(string="Tồn kho",digits="Product Unit of Measure",compute="_compute_qty_available",store=True)
    
    qty_income = fields.Float(string="Tổng nhập trong tháng",digits="Product Unit of Measure",compute="_compute_qty_income_outcome",store=True)
    qty_outcome = fields.Float(string="Tổng xuất sản xuất",digits="Product Unit of Measure",compute="_compute_qty_income_outcome",store=True)
    qty_outcome_sale = fields.Float(string="Tổng xuất bán",digits="Product Unit of Measure",compute="_compute_qty_income_outcome",store=True)
    
    @api.depends('product_id')
    def _compute_qty_available(self):
        for rec in self.sudo():
            qty_available = 0
            location_ids = self.env['stock.warehouse'].sudo().search([]).mapped('lot_stock_id')
            for location_id in location_ids:
                qty_available += rec.product_id.with_context(location=location_id.id).qty_available
            rec.qty_available = qty_available
            
    @api.depends('product_id','service_id')
    def _compute_product_uom_id(self):
        for line in self:
            if line.service_id:
                line.product_uom_id = line.service_id.uom_id
            elif line.product_id:
                line.product_uom_id = line.product_id.uom_id
            else:
                line.product_uom_id = False
    
    @api.onchange('warehouse_id', 'product_id', 'partner_id')
    def _onchange_warehouse_account_auto_picking_type(self):
        for rec in self:
            if not rec.warehouse_id:
                continue

            mapping_obj = self.env['picking.type.mapping']
            found_mapping = False

            # 1. Tìm khớp cả Kho + Sản phẩm + Liên hệ (trong danh sách partner_ids)
            if rec.product_id and rec.partner_id:
                found_mapping = mapping_obj.search([
                    ('warehouse_id', '=', rec.warehouse_id.id),
                    ('product_id', '=', rec.product_id.id),
                    ('partner_ids', 'in', [rec.partner_id.id])
                ], limit=1)

            # 2. Tìm theo Kho + Sản phẩm (Quy tắc cho tất cả liên hệ của sản phẩm này)
            if not found_mapping and rec.product_id:
                found_mapping = mapping_obj.search([
                    ('warehouse_id', '=', rec.warehouse_id.id),
                    ('product_id', '=', rec.product_id.id),
                    ('partner_ids', '=', False)
                ], limit=1)

            # 3. Tìm theo Kho + Liên hệ (Quy tắc cho tất cả sản phẩm của liên hệ này)
            if not found_mapping and rec.partner_id:
                found_mapping = mapping_obj.search([
                    ('warehouse_id', '=', rec.warehouse_id.id),
                    ('partner_ids', 'in', [rec.partner_id.id]),
                    ('product_id', '=', False)
                ], limit=1)

            # 4. Tìm theo Kho duy nhất (Quy tắc chung cho tất cả SP và tất cả LH trong kho này)
            if not found_mapping:
                found_mapping = mapping_obj.search([
                    ('warehouse_id', '=', rec.warehouse_id.id),
                    ('product_id', '=', False),
                    ('partner_ids', '=', False)
                ], limit=1)

            if found_mapping:
                rec.picking_type_id = found_mapping.picking_type_id.id

    @api.depends('service_id','product_id','approval_request_id.date','approval_request_id.department_id')
    def _compute_qty_income_outcome(self):
        env_params = self.env['ir.config_parameter'].sudo()
        sm_env = self.env['stock.move.line'].sudo()
        cn_env = self.env['enter.daily.work.output.other'].sudo()
        sx_ids = ast.literal_eval(env_params.get_param('ccv_custom_field.sx_ids', '[]'))
        for rec in self.sudo():
            qty_income = 0
            qty_outcome = 0
            qty_outcome_sale = 0
            if rec.service_id and rec.product_id:
                cn_ids = cn_env.search([('product_id','=',rec.service_id.id),('date','=', rec.approval_request_id.date.date()),('department_ids', 'in', [rec.approval_request_id.department_id.id]),])
                start_datetime = fields.Datetime.start_of(fields.Datetime.to_datetime(rec.approval_request_id.date), 'day')
                # start_datetime = fields.Datetime.to_datetime(rec.approval_request_id.date)
                start_of_month = start_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                last_day_of_month = calendar.monthrange(start_datetime.year, start_datetime.month)[1]
                end_of_month = start_datetime.replace(day=last_day_of_month, hour=23, minute=59, second=59, microsecond=999999)
                end_datetime = fields.Datetime.end_of(fields.Datetime.to_datetime(rec.approval_request_id.date), 'day')
                
                # Nhập
                move_ids = sm_env.search([
                    ('picking_id', '!=', False),
                    ('picking_id.stock_date_receipt', '>=', start_of_month.strftime('%Y-%m-%d %H:%M:%S')),
                    ('picking_id.stock_date_receipt', '<=', end_of_month.strftime('%Y-%m-%d %H:%M:%S')),
                    ('state', '=', 'done'),
                    ('product_id', '=', rec.product_id.id),
                    # ('picking_id.department_ids', 'in', [rec.approval_request_id.department_id.id]),
                    ('location_dest_id.warehouse_id', 'in', sx_ids),
                ]).sorted('date')
                # qty_income = sum([(move_id.qty_done / len(move_id.picking_id.department_ids)) for move_id in move_ids])
                qty_income = sum([(move_id.qty_done) for move_id in move_ids])
                qty_income = (qty_income - sum(cn_ids.mapped('production_other'))) if qty_income else qty_income
                
                # Xuất
                move_raw_ids = sm_env.search([
                    ('move_id.raw_material_production_id', '!=', False),
                    ('move_id.raw_material_production_id.stock_date_receipt', '>=', start_datetime.strftime('%Y-%m-%d %H:%M:%S')),
                    ('move_id.raw_material_production_id.stock_date_receipt', '<=', end_datetime.strftime('%Y-%m-%d %H:%M:%S')),
                    ('state', '=', 'done'),
                    ('product_id', '=', rec.product_id.id),
                    ('move_id.raw_material_production_id.department_ids', 'in', [rec.approval_request_id.department_id.id]),
                ]).sorted('date')
                qty_outcome = sum([(move_raw_id.qty_done / len(move_raw_id.move_id.raw_material_production_id.department_ids)) for move_raw_id in move_raw_ids])
                qty_outcome = (qty_outcome - sum(cn_ids.mapped('production_other'))) if qty_outcome else qty_outcome

                # Xuất bán
                move_sale_ids = sm_env.search([
                    ('picking_id', '!=', False),
                    ('picking_id.stock_date_receipt', '>=', start_datetime.strftime('%Y-%m-%d %H:%M:%S')),
                    ('picking_id.stock_date_receipt', '<=', end_datetime.strftime('%Y-%m-%d %H:%M:%S')),
                    ('state', '=', 'done'),
                    ('product_id', '=', rec.product_id.id),
                    ('picking_id.department_ids', 'in', [rec.approval_request_id.department_id.id]),
                    '|',
                    ('location_id.usage', '=', 'customer'),
                    ('location_dest_id.usage', '=', 'customer'),
                ]).sorted('date')
                qty_outcome_sale = sum([(move_sale_id.qty_done * (1 if move_sale_id.location_dest_id.usage == 'customer' else -1)) for move_sale_id in move_sale_ids])
                
            rec.qty_income = qty_income
            rec.qty_outcome = qty_outcome
            rec.qty_outcome_sale = qty_outcome_sale

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        view_record = self.env.ref('approvals.approval_product_line_view_tree', raise_if_not_found=False).sudo()

        if view_type == 'tree' and view.model == self._name and view.id == view_record.id:
            params = self.env.context.get('params')
            if params:
                record_id = params.get('id', False)
                model = params.get('model', False)
                if record_id and model == 'approval.request':
                    record = self.env[model].browse(record_id)
                    show_ton_kho_label = record.has_qty_produced != 'no'
                    for node in arch.xpath("//field[@name='quantity']"):
                        if show_ton_kho_label:
                            node.set('string', 'Tồn kho')
                        else:
                            node.set('string', 'Số lượng')
        return arch, view
    
    def _log_message(self, record, line, template, vals):
        data = vals.copy()
        if 'service_id' in vals:
            data['service_id'] = self.env['product.product'].browse(vals.get('service_id')).display_name
        if 'product_id' in vals:
            data['product_id'] = self.env['product.product'].browse(vals.get('product_id')).display_name
        record.message_post_with_view(template, values={'line': line, 'vals': dict(vals, **data)}, subtype_id=self.env.ref('mail.mt_note').id)

    def write(self, vals):
        mls = self.filtered(lambda ml: ml.approval_request_id.request_status not in ('new','cancel'))
        for line in mls:
            line._log_message(line.approval_request_id, line, 'ccv_custom_field.track_product_line_approvals_template', vals)
        res = super(ApprovalProductLine,self).write(vals)
        return res
