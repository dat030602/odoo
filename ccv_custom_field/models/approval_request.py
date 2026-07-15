from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from bs4 import BeautifulSoup
import logging
import datetime
import pytz

_logger = logging.getLogger(__name__)

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    picking_count = fields.Integer(string="Số phiếu xuất", compute="_compute_picking_count")
    has_picking = fields.Selection(string="Tạo phiếu kho", related="category_id.has_picking")

    rent_line_ids = fields.One2many('approvals.rent.line', 'approval_id')
    has_rent = fields.Selection(string="Thuê xe", related='category_id.has_rent')
    has_partner_in_product = fields.Selection(string='Chọn liên hệ trong sản phẩm', related='category_id.has_partner_in_product')
    has_image_in_product = fields.Selection(string='Hình ảnh trong sản phẩm', related="category_id.has_image_in_product")
    has_line_image = fields.Selection(string='Hình ảnh', related="category_id.has_line_image")

    has_team_id = fields.Selection(string='Chọn đội ngũ kinh doanh', related="category_id.has_team_id")

    has_reason = fields.Selection(string='Hiển thị lý do', related="category_id.has_reason")

    has_count_production = fields.Selection(string='Hiển thị số lần sản xuất', related="category_id.has_count_production")

    has_count_stock = fields.Selection(string='Hiển thị số lần tồn kho', related="category_id.has_count_stock")
    has_qty_produced = fields.Selection(string='Hiển thị số lượng sản xuất', related="category_id.has_qty_produced")
    has_qty_bb_used = fields.Selection(string='Số lượng BB đã sử dụng', related="category_id.has_qty_bb_used")
    has_note_in_product = fields.Selection(string='Ghi chú trong sản phẩm', related="category_id.has_note_in_product")
    has_mkt_comment = fields.Selection(string='Ý kiến MKT', related="category_id.has_mkt_comment")
    has_stock_in_product = fields.Selection(string='Tồn kho trong sản phẩm', related="category_id.has_stock_in_product")
    has_service_in_product = fields.Selection(string='Dịch vụ trong sản phẩm', related="category_id.has_service_in_product")
    has_qty_income_in_product = fields.Selection(string='SL nhập trong sản phẩm', related="category_id.has_qty_income_in_product")
    has_qty_outcome_in_product = fields.Selection(string='SL xuất trong sản phẩm', related="category_id.has_qty_outcome_in_product")
    has_department_id = fields.Selection(string='Chọn phòng ban', related="category_id.has_department_id")
    has_create_daily_work_output_other = fields.Selection(string='Hiển thị nút đẩy lương', related="category_id.has_create_daily_work_output_other")
    has_purchase = fields.Selection(string='Xem đơn mua hàng', related="category_id.has_purchase")
    has_sale_ids = fields.Selection(string='Chọn đơn bán hàng', related="category_id.has_sale_ids")
    has_picking_type = fields.Selection(string='Chọn loại hoạt động', related="category_id.has_picking_type")
    has_warehouse = fields.Selection(string='Chọn kho', related="category_id.has_warehouse")

    picking_type_id = fields.Many2one('stock.picking.type', string='Loại hoạt động')
    department_id = fields.Many2one('hr.department',string="Phòng ban")
    sale_order_id = fields.Many2one('sale.order', string="Mã đơn hàng")

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        for rec in self:
            if rec.sale_order_id:
                rec.partner_id = rec.sale_order_id.partner_id
                rec.team_id = rec.sale_order_id.team_id

    summary_info = fields.Html(string='Thông tin tóm tắt', compute='_compute_summary_info')
    show_history = fields.Boolean(string='Hiển thị lịch sử', default=False)

    def action_toggle_history(self):
        """Toggle hiển thị/ẩn tab lịch sử"""
        self.ensure_one()
        self.show_history = not self.show_history

    team_id = fields.Many2one('crm.team',string="Đội ngũ kinh doanh",groups="sales_team.group_sale_salesman")
    description = fields.Text(string='Diễn giải')
    description_convert = fields.Char(string='Diễn giải (ẩn)',compute="_compute_description_convert")

    count_production = fields.Char(string='Số lần sản xuất',default="   /   ")
    count_stock = fields.Text(string='Số lần tồn kho',default="   /   ")
    count_po = fields.Integer(string='Mua hàng',compute="_compute_count_po")
    purchase_ids = fields.Many2many('purchase.order',string='Mua hàng',compute="_compute_count_po")
    sale_ids = fields.Many2many('sale.order',string='Bán hàng', groups="sales_team.group_sale_salesman")
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        utc_now = fields.Datetime.now()
        user_tz = self.env.user.tz or 'UTC'
        timezone = pytz.timezone(user_tz)
        localized_time = pytz.utc.localize(utc_now).astimezone(timezone).replace(tzinfo=None)
        res['date'] = localized_time.date().strftime('%Y-%m-%d %H:%M:%S')
        res['department_id'] = self.env.user.sudo().employee_id.department_id
        return res
    
    def action_confirm(self):
        """Override để kiểm tra các trường bắt buộc trong dòng sản phẩm trước khi gửi đề xuất."""
        for rec in self:
            if rec.product_line_ids:
                errors = []
                if rec.has_partner_in_product == 'required':
                    missing = rec.product_line_ids.filtered(lambda l: not l.partner_id)
                    if missing:
                        products = ', '.join(missing.mapped('product_id.display_name'))
                        errors.append(_('Vui lòng nhập Liên hệ cho các dòng sản phẩm: %s') % products)
                if rec.has_service_in_product == 'required':
                    missing = rec.product_line_ids.filtered(lambda l: not l.service_id)
                    if missing:
                        products = ', '.join(missing.mapped('product_id.display_name'))
                        errors.append(_('Vui lòng nhập Dịch vụ cho các dòng sản phẩm: %s') % products)
                if rec.has_note_in_product == 'required':
                    missing = rec.product_line_ids.filtered(lambda l: not l.note)
                    if missing:
                        products = ', '.join(missing.mapped('product_id.display_name'))
                        errors.append(_('Vui lòng nhập Ghi chú cho các dòng sản phẩm: %s') % products)
                if errors:
                    raise ValidationError('\n'.join(errors))
        return super().action_confirm()

    @api.depends('name')
    def _compute_count_po(self):
        for rec in self:
            if rec.name:
                po_origin = rec.name.split('/')[1] if '/' in rec.name else rec.name
                po = self.env['purchase.order'].sudo().search([('origin', 'ilike', po_origin)])
                rec.purchase_ids = [(4, po_id) for po_id in po.ids]
                rec.count_po = len(po)
            else:
                rec.purchase_ids = False
                rec.count_po = 0
    
    def action_approve(self, approver=None):
        res = super().action_approve(approver=approver)
        for rec in self:
            if rec.request_status == 'approved':
                # Tự động tạo phiếu kho
                if rec.has_picking == 'required' or rec.has_picking_type != 'no':
                    rec._auto_create_all_pickings()

                if rec.has_sale_ids != 'no' and rec.sale_ids:
                    qty = {}
                    for line in rec.product_line_ids:
                        if line.product_id.type == 'service':
                            continue
                        if line.product_id.id not in qty:
                            qty[line.product_id.id] = 0
                        qty[line.product_id.id] += line.quantity + line.qty_produced
                    for order in rec.sale_ids:
                        if order.state in ['draft','sent']:
                            order.action_confirm()
                        for line in order.order_line:
                            if line.product_id.id not in qty:
                                line.qty_to_export = 0
                            else:
                                line.qty_to_export = min(qty[line.product_id.id], line.product_uom_qty - line.qty_delivered)
                                qty[line.product_id.id] -= line.qty_to_export
                        order.with_context(date=rec.date).action_launch_stock_rule()
                if rec.has_create_daily_work_output_other != 'no':
                    rec.sudo().action_create_daily_work_output_other()
        return res

    def _auto_create_all_pickings(self):
        """Tự động tạo tất cả phiếu kho dựa trên dòng sản phẩm"""
        self.ensure_one()
        # Gom nhóm theo Loại hoạt động và đối tác
        grouped_lines = {}
        for line in self.product_line_ids:
            if not line.product_id or line.product_id.type == 'service':
                continue
            
            # Ưu tiên lấy picking_type và warehouse từ dòng
            p_type = line.picking_type_id or self.picking_type_id or self.env['stock.picking.type'].browse(277)
            partner = line.partner_id or self.request_owner_id.partner_id
            warehouse = line.warehouse_id
            
            key = (p_type.id, partner.id, warehouse.id if warehouse else False)
            if key not in grouped_lines:
                grouped_lines[key] = self.env['approval.product.line']
            grouped_lines[key] |= line

        for (type_id, partner_id, warehouse_id), lines in grouped_lines.items():
            picking_type = self.env['stock.picking.type'].browse(type_id)
            partner = self.env['res.partner'].browse(partner_id)
            
            # Xác định Location từ picking type
            loc_src = picking_type.default_location_src_id.id
            loc_dest = picking_type.default_location_dest_id.id

            # Tạo phiếu kho
            reason = self.description_convert or self.name
            picking_vals = {
                'partner_id': partner.id,
                'picking_type_id': picking_type.id,
                'location_id': loc_src,
                'location_dest_id': loc_dest,
                'scheduled_date': self.date,
                'stock_date_receipt': self.date, # Gán theo ngày dùng tồn
                'origin': self.name,
                'reason_output_input_stock': reason,
                'driver_consignee_id': self.request_owner_id.id,
            }
            picking = self.env['stock.picking'].sudo().create(picking_vals)
            
            for line in lines:
                self.env['stock.move'].sudo().create({
                    'name': self.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'quantity_done': line.quantity,
                    'product_uom': line.product_uom_id.id,
                    'picking_id': picking.id,
                    'location_id': loc_src,
                    'location_dest_id': loc_dest,
                    'warehouse_id': warehouse_id or picking_type.warehouse_id.id,
                })
            
            # Xác nhận phiếu kho (để tạo bút toán tự động)
            try:
                picking.action_confirm()
                if picking.state != 'done':
                    picking.with_context(skip_immediate=True).button_validate()
            except Exception as e:
                # Quăng lỗi ra màn hình để chặn việc duyệt và nhắc liên hệ kế toán
                raise UserError(f"Lỗi kho: {str(e)}\n\n=> Vui lòng liên hệ kế toán để xử lý tồn kho trước khi duyệt lại!")

            # Cập nhật lại ngày hoàn tất để tránh Odoo ghi đè ngày hiện tại
            picking.sudo().write({'stock_date_receipt': self.date})

            # Ghi log vào chatter
            self.message_post(body=f"Đã tự động tạo và xác nhận phiếu kho: {picking._get_html_link()}")
    
    def action_view_purchase(self):
        self.ensure_one()
        purchase_ids = self.purchase_ids
        action = self.env['ir.actions.actions']._for_xml_id('purchase.purchase_rfq')
        if len(purchase_ids) > 1:
            action['domain'] = [('id', 'in', purchase_ids.ids)]
        elif len(purchase_ids) == 1:
            form_view = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = purchase_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
            
        return action

    @staticmethod
    def html_to_text(html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    @api.depends('description')
    def _compute_description_convert(self):
        for rec in self:
            if rec.description:
                rec.description_convert = rec.html_to_text(rec.description)
            else:
                rec.description_convert = False


    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = self.env['stock.picking'].search_count([('origin', '=', rec.name)])

    def action_view_related_pickings(self):
        self.ensure_one()
        pickings = self.env['stock.picking'].search([('origin', '=', self.name)])
        if len(pickings) == 1:
            return {
                'name': 'Phiếu xuất',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': pickings.id,
                'view_mode': 'form',
                'target': 'current',
            }
        elif len(pickings) > 1:
            return {
                'name': 'Phiếu xuất',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'tree,form',
                'target': 'current',
                'domain' : [('id','in', pickings.ids)]
            }

    def action_create_picking_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Tạo phiếu kho",
            'res_model': 'create.picking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_request_id': self.id,
                'default_picking_type_id': (self.product_line_ids.filtered(lambda l: l.picking_type_id).mapped('picking_type_id')[:1].id) or self.picking_type_id.id or 277,
            },
        }
        
    def action_create_mrp_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Tạo Lệnh sản xuất",
            'res_model': 'create.mrp.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_request_id': self.id,
            },
        }
    
    def action_view_daily_work_output_other(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Nhập sản lượng, công nhật",
            'res_model': 'enter.daily.work.output.other',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [('approval_id', '=', self.id)],
            'context': {
                'search_default_approval_id': self.id,
            },
        }
    
    def action_create_daily_work_output_other(self):
        self.ensure_one()
        service_ids = self.product_line_ids.mapped('service_id')
        to_create = []
        
        for service_id in service_ids:
            lines = self.product_line_ids.filtered(lambda l: l.service_id == service_id)
            
            existing_records = self.env['enter.daily.work.output.other'].search([
                ('product_id', '=', service_id.id),
                ('date', '=', self.date),
                ('approval_id', '=', self.id)
            ])

            if existing_records:
                existing_records.write({
                    'production_other': sum(lines.mapped('quantity')),
                    'price_unit': service_id.unit_price_cal_out_worker,
                    'department_ids': [(4, self.department_id.id)],
                })
            else:
                to_create.append({
                    'date': self.date,
                    'product_id': service_id.id,
                    'production_other': sum(lines.mapped('quantity')),
                    'price_unit': service_id.unit_price_cal_out_worker,
                    'department_ids': [(4, self.department_id.id)],
                    'approval_id': self.id,
                })
        if to_create:
            self.env['enter.daily.work.output.other'].create(to_create)

    def action_batch_create_daily_work_output(self):
        """Áp dụng hàng loạt cho các đơn đã phê duyệt chưa có công nhật"""
        records = self.filtered(lambda r: r.request_status == 'approved' and r.has_create_daily_work_output_other != 'no')
        for rec in records:
            rec.sudo().action_create_daily_work_output_other()
        return True

    def action_reset_qty_mrp_pk(self):
        self.product_line_ids._compute_qty_income_outcome()
        
    
    @api.depends('request_owner_id', 'category_id', 'product_line_ids')
    def _compute_summary_info(self):
        for rec in self:
            if rec.request_owner_id and rec.category_id and rec.id:
                # Lây danh sach san pham cua de xuat hien tai
                current_products = rec.product_line_ids.mapped('product_id')
                
                if current_products:
                    # Tim cac de xuat cu co cung san pham
                    history = self.search([
                        ('request_owner_id', '=', rec.request_owner_id.id),
                        ('category_id', '=', rec.category_id.id),
                        ('id', '!=', rec.id),
                        ('request_status', 'in', ['approved', 'refused']),
                        ('product_line_ids.product_id', 'in', current_products.ids)
                    ], order='date desc')
                else:
                    # Neu khong co san pham, khong hien thi gi
                    rec.summary_info = ""
                    continue
                
                # Tính summary - chi hien thi san pham chung
                if history:
                    summary_lines = []
                    product_totals = {}  # {product_id: total_quantity}
                    
                    for hist in history:
                        if hist.date and hist.product_line_ids:
                            # Chi lay cac san pham trung lap voi de xuat hien tai
                            common_products = hist.product_line_ids.filtered(
                                lambda line: line.product_id in current_products
                            )
                            
                            if common_products:
                                date_str = hist.date.strftime('%d/%m/%Y')
                                # Hien thi chi tiet tung san pham
                                product_details = []
                                for product in current_products:
                                    product_lines = common_products.filtered(lambda line: line.product_id == product)
                                    if product_lines:
                                        qty = sum(product_lines.mapped('quantity'))
                                        product_details.append(f"{qty} {product.uom_id.name if product.uom_id else ''} {product.name}")
                                        # Cong vao tong theo tung san pham
                                        if product.id not in product_totals:
                                            product_totals[product.id] = 0
                                        product_totals[product.id] += qty
                                
                                if product_details:
                                    url = f"/web#id={hist.id}&model={hist._name}&view_type=form"
                                    summary_lines.append(f"<a href='{url}'>Ngày {date_str} {rec.request_owner_id.name} đã đề xuất {', '.join(product_details)}</a>")
                    
                    # Them dong phan cach va tong theo tung san pham
                    if summary_lines and product_totals:
                        summary_lines.append("==========================================")
                        total_details = []
                        for product_id, total_qty in product_totals.items():
                            product = self.env['product.product'].browse(product_id)
                            total_details.append(f"{total_qty} {product.uom_id.name if product.uom_id else ''} {product.name}")
                        summary_lines.append(f"<b>TỔNG CỘNG:</b><br/>{'<br/>'.join(total_details)}")
                    
                    rec.summary_info = '<br/>'.join(summary_lines) if summary_lines else ""
                else:
                    rec.summary_info = ""
            else:
                rec.summary_info = ""


    def action_create_mrp(self):
        self.ensure_one()
        

