# -*- coding: utf-8 -*-
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import datetime
import json
import logging
import re

_logger = logging.getLogger(__name__)


class SaleVehicleConveyorMapping(models.Model):
    _name = "sale.vehicle.conveyor.mapping"
    _description = "Vehicle Conveyor Mapping"
    _rec_name = "conveyor_gate"

    conveyor_gate = fields.Char(string="Băng tải cửa", required=True)
    conveyor_line_id = fields.Char(string="ID băng tải", required=True)


class SaleVehicleInOutLine(models.Model):
    _name        = "sale.vehicle.in.out.line"
    _description = "Vehicle In/Out Line"

    name = fields.Char("Receipt Number", copy=False)

    is_warehouse_readonly = fields.Boolean(compute='_compute_is_warehouse_readonly')

    def _compute_is_warehouse_readonly(self):
        for rec in self:
            rec.is_warehouse_readonly = self.env.user.has_group('ccv_api_connector.group_vehicle_warehouse_readonly')

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        
        is_warehouse = self.env.user.has_group('ccv_api_connector.group_vehicle_warehouse_readonly')
        is_baove = self.env.user.has_group('ccv_api_connector.group_vehicle_security')
        is_main = self.env.user.has_group('ccv_api_connector.group_vehicle_main_action')
        is_invite = self.env.user.has_group('ccv_api_connector.group_vehicle_invite_only')
        is_complete = self.env.user.has_group('ccv_api_connector.group_vehicle_complete_only')
        is_out = self.env.user.has_group('ccv_api_connector.group_vehicle_out_confirm')
        is_admin = self.env.user.has_group('ccv_api_connector.group_admin')
        
        any_security = is_baove or is_main or is_invite or is_complete or is_out
        
        if True:
            doc = etree.XML(res['arch'])
            if view_type in ('form', 'tree', 'kanban'):
                if is_warehouse:
                    doc.set('create', '0')
                    doc.set('edit', '0')
                    doc.set('delete', '0')
                elif is_out or is_admin:
                    doc.set('delete', '1')
                elif any_security:
                    doc.set('create', '0')
                    doc.set('delete', '0')
                    if not (is_main or is_invite or is_complete):
                        doc.set('edit', '0')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
        
    is_baove_only = fields.Boolean(compute='_compute_is_baove_only', store=False)
    
    @api.depends_context('uid')
    def _compute_is_baove_only(self):
        # Admin is not baove only
        is_admin = self.env.user.has_group('ccv_api_connector.group_admin')
        
        is_baove = self.env.user.has_group('ccv_api_connector.group_vehicle_security')
        is_main = self.env.user.has_group('ccv_api_connector.group_vehicle_main_action')
        is_invite = self.env.user.has_group('ccv_api_connector.group_vehicle_invite_only')
        is_complete = self.env.user.has_group('ccv_api_connector.group_vehicle_complete_only')
        is_out = self.env.user.has_group('ccv_api_connector.group_vehicle_out_confirm')
        
        any_security = is_baove or is_main or is_invite or is_complete or is_out
        
        for rec in self:
            rec.is_baove_only = any_security and not is_admin and not is_out and not is_invite

    type = fields.Selection(
        string="Type",
        selection=[
            ("in", "In"),
            ("out", "Out"),
        ],
        default="out",
    )
    vehicle_num = fields.Char("Vehicle Number")
    vehicle_driver = fields.Char("Driver")
    partner_name = fields.Char("Customer/Supplier")
    quantity = fields.Float(string="Quantity", digits="Product Unit of Measure", compute="_compute_quantity", store=True)
    quantity_plan = fields.Float(string="Planning Quantity", digits="Product Unit of Measure", compute="_compute_quantity", store=True)
    bag_number = fields.Integer(string="Bag Number", compute="_compute_quantity")
    quantity_stock = fields.Float(string="SL nhu cầu", compute="_compute_quantity", digits="Product Unit of Measure")
    quantity_done_stock = fields.Float(string="SL hoàn tất", compute="_compute_quantity", digits="Product Unit of Measure")
    quantity_bag = fields.Integer(string="SL bao", compute="_compute_quantity")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    uom_number = fields.Integer(string="Unit of Measure", default=1)
    date_in = fields.Datetime(string="Vehicle Arrival Time")
    gate = fields.Char(string="Gate")
    gate_id = fields.Many2one('sale.vehicle.conveyor.mapping', string="Cổng Xuất/Nhập", compute="_compute_gate_id", inverse="_inverse_gate_id")

    @api.depends("gate")
    def _compute_gate_id(self):
        for rec in self:
            if rec.gate:
                gate_str = rec.gate.strip().replace(" ", "-")
                mapping = self.env['sale.vehicle.conveyor.mapping'].sudo().search([('conveyor_gate', '=', gate_str)], limit=1)
                rec.gate_id = mapping
            else:
                rec.gate_id = False

    def _inverse_gate_id(self):
        for rec in self:
            if rec.gate_id:
                rec.gate = rec.gate_id.conveyor_gate
            else:
                rec.gate = False

    loading = fields.Char(string="Loading")
    loading2 = fields.Char(string="Bốc xếp 2")
    stocker = fields.Char(string="Stocker")
    date_start = fields.Datetime(string="Start Time")
    date_end = fields.Datetime(string="End Time")
    bom_time = fields.Float(string="Standard Time (Minutes)", digits=(16, 0))
    bom_time_over = fields.Float(string="Over Standard Time", digits=(16, 2))
    sale_vehicle_check_picking = fields.Boolean(string="Chưa có mã tham chiếu")
    note = fields.Char(string="Ghi chú", compute="_compute_note")
    user_note = fields.Char(string="Ghi chú", copy=False)
    is_next_day = fields.Boolean(string="Chuyển sang ngày hôm sau", copy=False)
    next_day = fields.Date(string="Ngày chuyển", copy=False)
    is_carried_over = fields.Boolean(string="Chuyển từ ngày trước", copy=False)

    loading_id = fields.Many2one("hr.department", string="Loading", compute="_compute_loading_id", inverse="_inverse_loading_id")
    loading2_id = fields.Many2one("hr.department", string="Bốc xếp 2", compute="_compute_loading2_id", inverse="_inverse_loading2_id")
    has_stocker = fields.Boolean(compute="_compute_has_stocker")
    has_loading = fields.Boolean(compute="_compute_has_loading")
    has_loading2 = fields.Boolean(compute="_compute_has_loading2")
    stocker_id = fields.Many2one("res.users", string="Stocker", compute="_compute_stocker_id", inverse="_inverse_stocker_id")
    create_at = fields.Datetime(string="Create Time", default=fields.Datetime.now)
    status = fields.Selection(
        string="Status",
        selection=[
            ("open", "Open"),
            ("lock", "Locked"),
        ],
        related="sale_vehicle_id.status",
    )
    to_push = fields.Boolean(string="Cần đẩy ", copy=False)

    canxe_status = fields.Selection([
        ('dang_ky', 'Đăng ký'),
        ('dang_cho', 'Chờ vào cân'),
        ('chuan_bi', 'Chờ xuất nhập'),
        ('moi_vao', 'Đang xuất nhập'),
        ('xuat_nhap', 'Xe chờ ra'),
        ('hoan_thanh', 'Xe đã ra cổng'),
        ('ra_cong', 'Đã ra cổng (cũ)'),
    ], string="Trạng thái", default='dang_ky', tracking=True)

    def _speak_notification(self, text_to_speak):
        if self.sale_vehicle_id and getattr(self.sale_vehicle_id, 'ra_loa', False):
            repeated_text = f"{text_to_speak} {text_to_speak}"
            self.env['bus.bus']._sendone('ccv_tts_channel', 'ccv_tts_speak', {'text': repeated_text, 'vehicle_id': self.sale_vehicle_id.id})

    def action_xac_nhan(self):
        for rec in self:
            if rec.canxe_status == 'dang_ky':
                if not rec.name or not rec.name.startswith('CCV-'):
                    today = fields.Date.context_today(rec)
                    prefix = f"CCV-{today.strftime('%y%m%d')}"
                    last_record = self.env['sale.vehicle.in.out.line'].search(
                        [('name', '=like', f"{prefix}%")],
                        order='name desc',
                        limit=1
                    )
                    last_seq = 0
                    if last_record and last_record.name:
                        try:
                            last_seq = int(last_record.name[-3:])
                        except ValueError:
                            pass
                    rec.name = f"{prefix}{last_seq + 1:03d}"

                rec.canxe_status = 'dang_cho'
                rec.date_in = fields.Datetime.now()
                type_str = 'nhập' if rec.type == 'in' else 'xuất'
                text_to_speak = f"Thông báo, Xe {type_str} có biển số, {rec.vehicle_num or ''} đã đến cổng."
                rec._speak_notification(text_to_speak)
                rec.action_gui_lenh_can()

    def action_can_xong(self):
        for rec in self:
            if rec.canxe_status == 'dang_cho':
                rec.canxe_status = 'chuan_bi'
                type_str = 'nhập' if rec.type == 'in' else 'xuất'
                text_to_speak = f"Thông báo, Xe có biển số, {rec.vehicle_num or ''} đã cân xong, đang chờ vào {type_str} hàng."
                rec._speak_notification(text_to_speak)

    def action_moi_vao(self):
        for rec in self:
            if rec.canxe_status == 'chuan_bi':
                rec.canxe_status = 'moi_vao'
                type_str = 'nhập' if rec.type == 'in' else 'xuất'
                gate_str = rec.gate or ""
                loading_str = ""
                if rec.loading_id or rec.loading2_id:
                    loadings = []
                    for l_obj in [rec.loading_id, rec.loading2_id]:
                        if l_obj and l_obj.name:
                            short_l_name = re.split(r'[,/\\]', l_obj.name)[-1].strip()
                            if short_l_name:
                                loadings.append(short_l_name)
                    loading_str = f"{' và '.join(loadings)}, " if loadings else ""
                stocker_str = ""
                if rec.stocker_id:
                    stocker_role = "nhà máy" if rec.type == 'in' else "thủ kho"
                    short_name = rec.stocker_id.name.split()[-1].capitalize() if rec.stocker_id.name else ""
                    stocker_str = f"{stocker_role} {short_name}, "
                
                text_to_speak = f"Thông báo, Mời xe có biển số, {rec.vehicle_num or ''} vào cửa ,{gate_str}, {loading_str}{stocker_str}thực hiện {type_str}."
                rec._speak_notification(text_to_speak)

    def action_xac_nhan_hoan_thanh(self):
        for rec in self:
            if rec.canxe_status == 'moi_vao':
                rec.canxe_status = 'xuat_nhap'
                type_str = 'nhập' if rec.type == 'in' else 'xuất'
                text_to_speak = f"Thông báo, Xe có biển số, {rec.vehicle_num or ''}, cửa số {rec.gate or ''} đã {type_str} xong. Mời ra cân xe làm thủ tục."
                rec._speak_notification(text_to_speak)

    def action_xac_nhan_ra_cong(self):
        is_admin = self.env.user.has_group('ccv_api_connector.group_admin')
        is_out = self.env.user.has_group('ccv_api_connector.group_vehicle_out_confirm')
        is_baove = self.env.user.has_group('ccv_api_connector.group_vehicle_security')

        for rec in self:
            da_can_lan_2 = bool(rec.weighing_ngay_can_2)

            if is_out and not is_admin:
                if rec.canxe_status == 'xuat_nhap':
                    if da_can_lan_2:
                        rec.canxe_status = 'hoan_thanh'
                        text_to_speak = f"Xin mời xe có biển số {rec.vehicle_num or ''} ra cổng, Chúc Quý khách thượng lộ bình an và hẹn gặp lại."
                        rec._speak_notification(text_to_speak)
                    else:
                        raise UserError(_("Xe chưa cân lần 2!"))

            elif is_baove and not is_admin:
                if rec.canxe_status == 'xuat_nhap':
                    if da_can_lan_2:
                        rec.canxe_status = 'hoan_thanh'
                        text_to_speak = f"Xin mời xe có biển số {rec.vehicle_num or ''} ra cổng, Chúc Quý khách thượng lộ bình an và hẹn gặp lại."
                        rec._speak_notification(text_to_speak)
                    else:
                        raise UserError(_("Xe chưa cân lần 2!"))

            else:
                if rec.canxe_status == 'xuat_nhap':
                    rec.canxe_status = 'hoan_thanh'
                    text_to_speak = f"Xin mời xe có biển số {rec.vehicle_num or ''} ra cổng, Chúc Quý khách thượng lộ bình an và hẹn gặp lại."
                    rec._speak_notification(text_to_speak)

    def baove_action(self):
        return self.action_xac_nhan()

    def write(self, vals):
        if 'canxe_status' in vals:
            status_order = {
                'dang_ky': 1,
                'dang_cho': 2,
                'chuan_bi': 3,
                'moi_vao': 4,
                'xuat_nhap': 5,
                'hoan_thanh': 6,
                'ra_cong': 7,
            }
            new_status = vals['canxe_status']
            new_idx = status_order.get(new_status, 0)
            
            for rec in self:
                old_status = rec.canxe_status or 'dang_ky'
                old_idx = status_order.get(old_status, 0)
                
                # Bỏ qua nếu giá trị không đổi
                if old_status == new_status:
                    continue
                
                # Bắt buộc trình tự phải là +1
                if new_idx - old_idx != 1:
                    raise UserError(_("Trạng thái cân xe phải chuyển tuần tự từ trên xuống dưới theo thứ tự:\n1. Đăng ký\n2. Chờ vào cân\n3. Chờ xuất nhập\n4. Đang xuất nhập\n5. Xe chờ ra\n6. Xe đã ra cổng\n\nKhông được nhảy cóc, không được quay ngược lại vì bất cứ lý do nào!"))

        if self.env.user.has_group('ccv_api_connector.group_vehicle_security') \
           and not self.env.user.has_group('ccv_api_connector.group_admin') \
           and not self.env.user.has_group('ccv_api_connector.group_vehicle_out_confirm') \
           and not self.env.user.has_group('ccv_api_connector.group_vehicle_invite_only'):
            allowed_fields = {'gate', 'canxe_status', 'date_in', 'weighing_history_ids'}
            for key in vals:
                if key not in allowed_fields:
                    raise UserError(_("Tài khoản Bảo vệ chỉ được phép điền 'Cửa Xuất Nhập' và bấm nút 'Xác nhận xe đến'."))
        return super(SaleVehicleInOutLine, self).write(vals)

    def dummy_action(self):
        # Hàm dummy giữ chỗ cho nút trên tree view để cột không bị ẩn
        pass

    def action_open_popup(self):
        self.ensure_one()
        return {
            'name': 'Chi tiết',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.vehicle.in.out.line',
            'res_id': self.id,
            'target': 'new',
        }

    # ── Cân xe ────────────────────────────────────────────────────────────
    weighing_order_id  = fields.Many2one('stock.weighing.order', string="Order Id", copy=False)
    weighing_history_ids = fields.Char(string="Lịch sử Cân xe", copy=False)
    can_ip             = fields.Char(string="Scale IP", help="IP của máy cân")
    weighing_so_phieu  = fields.Char('Số phiếu cân',   default=False)
    # Giữ Char như cũ để tương thích schema DB — hiển thị số dạng text
    weighing_tl_lan1   = fields.Char('TL lần 1 (Tấn)',  default=False)
    weighing_tl_lan2   = fields.Char('TL lần 2 (Tấn)',  default=False)
    weighing_tl_hang   = fields.Char('TL hàng (Tấn)',   default=False)
    weighing_tl_bao_bi = fields.Char('TL bao bì (Tấn)', default=False)
    odoo_tl_bao_bi     = fields.Float('Odoo TL bao bì (tấn)', compute="_compute_odoo_tl_bao_bi", digits=(16, 5))
    weighing_tl_sau_tru_bao_bi = fields.Char('TL sau trừ bao bì (Tấn)', default=False)
    weighing_ngay_can_1 = fields.Datetime('Ngày cân lần 1', default=False)
    weighing_ngay_can_2 = fields.Datetime('Ngày cân lần 2', default=False)
    weighing_nhan_vien  = fields.Char('Nhân viên cân điện tử', default=False)
    weighing_nhan_vien_bam_can = fields.Char('Nhân viên gửi lệnh cân', default=False)
    weighing_is_export  = fields.Boolean('Xuất hàng',  default=False)

    has_link_line  = fields.Boolean(copy=False)
    sale_order_ids = fields.Many2many(
        "sale.order",
        "sale_vehicle_in_out_line_sale_order_rel",
        "vehicle_line_id",
        "sale_order_id",
        string="Sale Orders",
    )
    purchase_order_ids = fields.Many2many(
        "purchase.order",
        "sale_vehicle_in_out_line_purchase_order_rel",
        "vehicle_line_id",
        "purchase_order_id",
        string="Purchase Orders",
    )
    picking_id = fields.Many2many(
        "stock.picking",
        "sale_vehicle_in_out_line_picking_rel",
        "vehicle_line_id",
        "picking_id",
        string="Mã tham chiếu",
    )

    # ════════════════════════════════════════════════════════════════════
    #  GỬI LỆNH CÂN → MÁY CÂN
    # ════════════════════════════════════════════════════════════════════
    def action_gui_lenh_can(self):
        self.ensure_one()

        # 1. Lấy đơn hàng
        order = (
            self.sale_order_ids[0]
            if self.sale_order_ids
            else self.purchase_order_ids[0]
            if self.purchase_order_ids
            else False
        )

        # 2. Lấy picking
        picking = False
        if self.picking_id:
            picking = self.picking_id
        else:
            p = self._prepare_picking_to_push(
                self.sale_vehicle_id.date, self.date_end is not False)
            picking = p if p else False

        # 3. Lấy product an toàn (tránh IndexError)
        product = False
        if picking and picking.mapped('move_ids'):
            product = picking.mapped('move_ids')[0].product_id

        ex_quanity = 0.0
        try:
            ex_quanity = self.quantity_stock or 0.0
            if self.uom_id and "t" in self.uom_id.name.lower():
                ex_quanity = ex_quanity * 1000.0
        except Exception as e:
            _logger.error("[SmartWeight] Lỗi khi tính ex_quanity: %s", e)
            ex_quanity = 0.0

        # 3.5. Tính toán trọng lượng bao bì (tl_bao_bi)
        # tl_bao_bi = 0.0
        # if picking:
        #     for move in picking.move_ids:
        #         if move.product_id and hasattr(move.product_id, 'packaging_specification_id') and move.product_id.packaging_specification_id:
        #             tl_bao_bi += (move.bag_number or 0.0) * move.product_id.packaging_specification_id.factor
        # self.weighing_tl_bao_bi = str(tl_bao_bi)

        # 4. Tạo hoặc dùng lại weighing order
        weigh_order = None
        try:
            if not self.weighing_order_id:
                weigh_order = self.env['stock.weighing.order'].create({
                    'name'         : self.name or _('New'),
                    'sale_id'      : order.id if order and order._name == 'sale.order' else False,
                    'picking_id'   : picking[0].id if picking else False,
                    'partner_id'   : order.partner_id.id if order and order.partner_id else False,
                    'product_id'   : product.id if product else False,
                    'license_plate': self.vehicle_num,
                    'expected_qty' : ex_quanity,
                    'vehicle_line_id': self.id,
                    'is_export'    : self.type == 'out',
                })
                self.weighing_order_id = weigh_order
            else:
                weigh_order = self.weighing_order_id
            
            if not self.weighing_history_ids and weigh_order:
                self.weighing_history_ids = str(weigh_order.id)
        except Exception as e:
            _logger.error("[SmartWeight] Lỗi khi tạo weighing order: %s", e)
            raise UserError(_("Lỗi khi tạo weighing order: %s" % e))


        # 5. Chuẩn bị payload gửi máy cân
        payload = {
            "OrderId"      : weigh_order.id,
            "OrderName"    : weigh_order.name,
            "LicensePlate" : self.vehicle_num or "",
            "PartnerName"  : self.partner_name or "",
            "ProductName"  : product.name if product else "",
            "IsExport"     : self.type == 'out',
            "ExpectedQty"  : ex_quanity,
            "TrongLuongBi" :  round((self.odoo_tl_bao_bi or 0.0) * 1000, 2),
            "SoChungTu"    : ", ".join(picking.mapped('name')) if picking else "",
            "OdooPartnerId": order.partner_id.id if order and order.partner_id else 0,
            "OdooProductId": product.id if product else 0,
            "NgayXuatKH"   : fields.Datetime.now().isoformat(),
            "DriverName"   : self.vehicle_driver or "",
            "WarehouseName": (picking[0].location_id.warehouse_id.name
                              if picking and picking[0].location_id and
                                 picking[0].location_id.warehouse_id else ""),
            "Note"         : self.user_note or "",
        }

        # 6. Chốt dữ liệu xuống DB trước khi gọi API bên ngoài
        self.env.cr.commit()

        # 7. Gửi đến máy cân
        can_ip = self.can_ip or self.env['ir.config_parameter'].sudo().get_param('smartweight.ip',   '127.0.0.1')
        can_port = self.env['ir.config_parameter'].sudo().get_param('smartweight.port',  '8765')
        url = f"http://{can_ip}:{can_port}/weighorder"

        _logger.info("[SmartWeight] Gửi lệnh cân: url=%s, payload=%s", url, payload)

        try:
            resp   = requests.post(url, json=payload, timeout=10)
            result = resp.json()
            _logger.warning("Can xe log (get in 0) order: %s - Payload: %s - log time: %s", weigh_order.id, payload, (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'))
            if result.get('status') == 'received':
                _logger.warning("Can xe log (get in) order: %s - Payload: %s - log time: %s", weigh_order.id, payload, (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'))
                return {
                    'type': 'ir.actions.client',
                    'tag' : 'display_notification',
                    'params': {
                        'title'  : 'Thành công',
                        'message': f'Lệnh {weigh_order.name} đã gửi. Vui lòng chờ kết quả.',
                        'type'   : 'success',
                    }
                }
            else:
                raise UserError(_("Lỗi từ máy cân: %s") % result.get('message', 'Unknown'))
        except requests.exceptions.ConnectionError:
            raise UserError(_("Không kết nối được máy cân tại %s — kiểm tra IP/port và phần mềm cân đang chạy.") % url)
        except Exception as e:
            raise UserError(_("Lỗi: %s") % str(e))

    # ════════════════════════════════════════════════════════════════════
    # Giữ nguyên tất cả các method cũ bên dưới — không thay đổi
    # ════════════════════════════════════════════════════════════════════

    @api.depends(
        "sale_order_ids.picking_ids.move_ids.bag_number",
        "purchase_order_ids.picking_ids.move_ids.bag_number",
        "sale_order_ids.picking_ids.move_ids.product_uom_qty",
        "purchase_order_ids.picking_ids.move_ids.product_uom_qty",
        "sale_order_ids.picking_ids.stock_date_receipt",
        "purchase_order_ids.picking_ids.stock_date_receipt",
        "picking_id.move_ids.bag_number",
        "picking_id.move_ids.product_uom_qty",
        "picking_id.move_ids.quantity_done",
        'date_end',
        'vehicle_num',
        'uom_id',
        'sale_vehicle_check_picking',
    )
    def _compute_quantity(self):
        for rec in self:
            date_record = getattr(rec.sale_vehicle_id, 'date', False) if rec.sale_vehicle_id else False
            lines = self.env['ccv.sale.plan.export'].sudo().search([
                ('date', '=', date_record),
                ('state', '=', 'locked'),
                ('type', '=', 'summary'),
            ], limit=1).line_ids.filtered(lambda l: l.order_id in rec.sale_order_ids and l.product_uom_id == rec.uom_id)
            rec.quantity_plan = sum(lines.mapped('qty_delivery'))
            quantity = rec.quantity
            if rec.sale_vehicle_check_picking:
                rec.bag_number = 0
                rec.quantity_stock = 0
                rec.quantity_bag = 0
                rec.quantity_done_stock = 0
                continue
            
            pickings_for_button = False
            # 1. Neu có picking_id (Mã tham chi) thì dùng nó
            if rec.picking_id:
                pickings_for_button = rec.picking_id
            # 2. Neu không có picking_id thì dùng logic cu (tù sale/purchase orders)
            else:
                order_ids = rec.sale_order_ids or rec.purchase_order_ids
                if order_ids:
                    # Lây tât ca phiêu kho tù don hàng
                    all_pickings = order_ids.picking_ids

                    pickings_for_button = all_pickings

            if pickings_for_button:
                rec.bag_number = sum(pickings_for_button.move_ids.mapped('bag_number'))
                rec.quantity_stock = sum(pickings_for_button.move_ids.mapped('product_uom_qty'))
                rec.quantity_done_stock = sum(pickings_for_button.move_ids.mapped('quantity_done'))
                rec.quantity_bag = sum(pickings_for_button.move_ids.mapped('bag_number'))
                
                # Logic tính odoo_tl_bao_bi đã được tách ra hàm _compute_odoo_tl_bao_bi
            else:
                rec.bag_number = 0
                rec.quantity_stock = 0
                rec.quantity_done_stock = 0
                rec.quantity_bag = 0
            rec.quantity = quantity


    @api.depends(
        "sale_order_ids.picking_ids.move_ids.bag_number",
        "purchase_order_ids.picking_ids.move_ids.bag_number",
        "picking_id.move_ids.bag_number",
        "sale_vehicle_check_picking"
    )
    def _compute_odoo_tl_bao_bi(self):
        for rec in self:
            if rec.sale_vehicle_check_picking:
                rec.odoo_tl_bao_bi = 0.0
                continue
                
            pickings_for_button = False
            if rec.picking_id:
                pickings_for_button = rec.picking_id
            # else:
            #     order_ids = rec.sale_order_ids or rec.purchase_order_ids
            #     if order_ids:
            #         all_pickings = order_ids.picking_ids
            #         pickings_for_button = all_pickings

            if pickings_for_button:
                tl_bao_bi = 0.0
                for move in pickings_for_button.move_ids:
                    if move.product_id and hasattr(move.product_id, 'packaging_specification_id') and move.product_id.packaging_specification_id:
                        # factor (Tỷ lệ) là số lượng bao/cái trong 1 Đơn vị gốc (1 Tấn)
                        # Khối lượng 1 bao (Tấn) = 1.0 / factor
                        factor = move.product_id.packaging_specification_id.factor
                        if factor:
                            tl_bao_bi += (move.bag_number or 0.0) / factor
                rec.odoo_tl_bao_bi = round(tl_bao_bi, 5)
            else:
                rec.odoo_tl_bao_bi = 0.0

    def _update_fields_to_picking(self, pickings):
        pickings.stocker_id = self.stocker_id
        pickings.department_ids = self.loading_id
        pickings.vehicle_driver_name = self.vehicle_driver
        pickings.vehicle_license_plate = self.vehicle_num
        pickings.time_start = self.date_start
        pickings.time_end = self.date_end
        pickings.total_time_vehicle = self.bom_time
        pickings.location_export = self.gate
        for picking in pickings:
            picking.export_at_ware = picking.location_id.warehouse_id.name

    def action_update_fields_to_picking(self):
        self.ensure_one()
        if self.picking_id:
            picking_ids = self.picking_id
        else:
            picking_ids = self._prepare_picking_to_push(self.sale_vehicle_id.date, self.date_end is not False)
        
        self._update_fields_to_picking(picking_ids)
        
        if self.has_loading and self.has_loading2 and len(picking_ids) == 2:
            picking_ids[0].department_ids = self.loading_id
            picking_ids[1].department_ids = self.loading2_id

    def action_view_picking(self):
        self.ensure_one()
        # Neu co picking_id (Ma tham chieu) duoc chon thi hien thi chi cac picking do
        if self.picking_id:
            picking_ids = self.picking_id
        else:
            # Neu khong co picking_id thi dung logic cu
            picking_ids = self._prepare_picking_to_push(self.sale_vehicle_id.date, self.date_end is not False)

        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        if len(picking_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = picking_ids.ids[0]
            action['target'] = 'new'
        else:
            action['domain'] = [('id', 'in', picking_ids.ids)]
        return action

    def action_view_sale_orders(self):
        self.ensure_one()
        action = self.env.ref('sale.action_orders').sudo().read()[0]
        if len(self.sale_order_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.sale_order_ids.ids[0]
        else:
            action['domain'] = [('id', 'in', self.sale_order_ids.ids)]
        return action

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env.ref('purchase.purchase_rfq').sudo().read()[0]
        if len(self.purchase_order_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.purchase_order_ids.ids[0]
            action['target'] = 'new'
        else:
            action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        return action

    def _prepare_picking_to_push(self, rp_date, is_done=False):
        self.ensure_one()
        domain_state = ('draft', 'waiting', 'confirmed', 'assigned') if not is_done else ('done')
        order_ids = self.sale_order_ids if self.sale_order_ids else self.purchase_order_ids
        default_picking = self.env['stock.picking']
        match_picking = default_picking
        is_import = False
        if self.purchase_order_ids and self.purchase_order_ids.stock_input_ids.picking_id:
            picking_ids = order_ids.stock_input_ids.picking_id
            is_import = True
        else:
            picking_ids = order_ids.picking_ids
        picking_ids = picking_ids.filtered(lambda l: l.state in domain_state and l.stock_date_receipt and l.stock_date_receipt.date() == rp_date)
        if is_import:
            match_picking = picking_ids.filtered(lambda l: l.vehicle_license_plate == self.vehicle_num)
            if not match_picking and self.vehicle_num:
                match_picking = picking_ids.filtered(lambda l: l.vehicle_license_plate is False)
                match_picking = picking_ids[0] if picking_ids else default_picking
        else:
            if len(picking_ids) > 1:
                match_picking_with_plate = picking_ids.filtered(lambda l: l.vehicle_license_plate == self.vehicle_num)
                if match_picking_with_plate:
                    match_picking = match_picking_with_plate
                else:
                    match_picking = picking_ids.filtered(lambda l: l.vehicle_license_plate is False)
                    match_picking = match_picking[0] if match_picking else match_picking
        return match_picking if match_picking else picking_ids

    def send_to_conveyor(self):
        self.ensure_one()
        self.env.cr.commit()
        Log = self.env['conveyor.log']

        picking_ids = self._prepare_picking_to_push(self.sale_vehicle_id.date, is_done=True)

        if self.type == 'out' and not picking_ids:
            picking_ids = self._prepare_picking_to_push(self.sale_vehicle_id.date)
        self._update_fields_to_picking(picking_ids)

        if self.type == 'in':
            if picking_ids:
                self.to_push = True
            return

        if not self.name:
            return

        _logger.info('Preparing to push data to conveyor for vehicle: %s', self.vehicle_num)
        _logger.info('Picking IDs: %s', picking_ids.ids)
        _logger.info('Quantity: %s', self.quantity)
        _logger.info('Name: %s', self.name)
        _logger.info('Gate: %s', self.gate)

        conveyor_lineid = '-1'
        if self.gate:
            gate = self.gate.strip().replace(" ", "-")
            conveyor_mapping = self.env['sale.vehicle.conveyor.mapping'].sudo().search([('conveyor_gate', '=', gate)], limit=1)
            if conveyor_mapping and conveyor_mapping.conveyor_line_id:
                conveyor_lineid = conveyor_mapping.conveyor_line_id.strip()

        if conveyor_lineid == '-1':
            return

        data = {
            'LineID': conveyor_lineid,
            "MO_Code": self.name,
            "MO_Custommer": self.partner_name,
            "MO_Tranz": self.vehicle_num,
            'MO_ChieuDH': 1,
            'SL_Tan': self.quantity,
            'MO_BocXep': self.loading_id.name if self.loading_id else self.loading,
            'MO_ThuKho': (self.stocker_id.name_without_position or self.stocker_id.name or "") if self.stocker_id else self.stocker,
            'Product': [],
        }
        bag_number = self.bag_number
        if bag_number == 0:
            for line in picking_ids.move_ids.filtered(lambda m: m.bag_number > 0 and m.location_dest_id.usage == 'customer'):
                if not line.product_id.default_code or not line.product_id.default_specification_id:
                    continue
                bag_number += line.bag_number

        if bag_number == 0:
            return

        product = self.env['mrp.production'].sudo().search([('state','=','done')], limit=1).product_id
        product_lengths = self.env['uom.uom'].search([('product_length','!=',0)]).mapped('product_length')
        if not product_lengths:
            return

        lenght_bag = sum(product_lengths) / len(product_lengths)

        data['Product'].append({
            "ProCode": product.default_code,
            "ProName": product.name,
            "ProLen": lenght_bag,
            'StartNum': 0,
            'PlanNum': bag_number,
        })
        params = {
            'Push_MO_Bagcounter': json.dumps(data),
        }
        _logger.info('$$$$$$$$$$$$$$$$$$$$ %s', data)
        res = Log.execute_api(self, data=params, is_push=True)
        self.to_push = True
        return res

    @api.onchange("quantity_stock", "quantity_done_stock")
    def _onchange_quantity_stock(self):
        for rec in self:
            if rec.quantity_done_stock > 0:
                rec.quantity = rec.quantity_done_stock
            else:
                rec.quantity = rec.quantity_stock

    @api.onchange("sale_order_ids", "purchase_order_ids")
    def _onchange_partner_name(self):
        for rec in self:
            names = []
            # Lấy thông tin từ sale_order_ids
            for idx, order in enumerate(rec.sale_order_ids):
                abbr = order.abbreviation or ""
                if abbr:
                    code = order.team_id.code if order.team_id else ""
                    if idx == 0 and code and abbr:
                        name = f"{code} - {abbr}"
                    elif abbr:
                        name = f"{abbr}"
                    else:
                        name = ""
                    if name and (not any(name in n for n in names)):
                        names.append(name)
            # Lấy thông tin từ purchase_order_ids
            for idx, order in enumerate(rec.purchase_order_ids):
                code = "TM"
                abbr = order.abbreviation if hasattr(order, "abbreviation") else ""
                if abbr:
                    if idx == 0 and code and abbr:
                        name = f"{code} - {abbr}"
                    elif abbr:
                        name = f"{abbr}"
                    else:
                        name = ""

                    if name and (not any(name in n for n in names)):
                        names.append(name)
            if names:
                rec.partner_name = " + ".join(names)

    sale_vehicle_id = fields.Many2one("sale.vehicle.in.out")

    def action_delete_self(self):
        parent = self.sale_vehicle_id
        self.unlink()
        if parent:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.vehicle.in.out',
                'res_id': parent.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange("vehicle_num")
    def _onchange_vehicle_num(self):
        if self.vehicle_num:
            import re

            # Bỏ hết các ký tự đặc biệt, chỉ lấy số và chữ
            plate = (
                self.vehicle_num.replace(" ", "")
                .replace(".", "")
                .replace(",", "")
                .replace("_", "")
                .replace("-", "")
            )
            matches = []
            # Tìm pattern: 2 số, 1 chữ, 4-5 số (cho phép 4 hoặc 5 số cuối)
            pattern = re.compile(r"(\d{2})([A-Z])(\d{5})", re.IGNORECASE)
            result = pattern.search(plate)
            if result:
                num1, char, num2 = result.groups()
                if len(num2) == 4:
                    num2 = "0" + num2
                # Không thêm dấu gạch nối
                formatted_plate = f"{num1}{char.upper()}{num2}"
                matches = [formatted_plate]
            if matches:
                self.vehicle_num = matches[0].strip()

    @api.depends("user_note", "is_next_day")
    def _compute_note(self):
        for rec in self:
            if rec.is_next_day:
                data = (
                    self.env["sale.vehicle.mapping"]
                    .sudo()
                    .search([("model", "=", "data.note")], limit=1)
                )
            else:
                data = (
                    self.env["sale.vehicle.mapping"]
                    .sudo()
                    .search(
                        [
                            ("model", "=", "data.note"),
                            ("key", "ilike", str(rec.user_note)),
                        ],
                        limit=1,
                    )
                )
            rec.note = data.record_id if data else rec.user_note

    @api.model
    def default_get(self, fields_list):
        defaults = super(SaleVehicleInOutLine, self).default_get(fields_list)
        defaults["uom_id"] = 28
        return defaults

    @api.depends("stocker_id")
    def _compute_has_stocker(self):
        for rec in self:
            rec.has_stocker = True if rec.stocker_id else False

    @api.depends("loading_id")
    def _compute_has_loading(self):
        for rec in self:
            rec.has_loading = True if rec.loading_id else False

    @api.depends("loading2_id")
    def _compute_has_loading2(self):
        for rec in self:
            rec.has_loading2 = True if rec.loading2_id else False

    @api.depends("uom_id")
    def _compute_uom_id(self):
        for rec in self:
            model = "uom.uom"
            uom_number = 1
            if rec.uom_id:
                mapping_id = self.env["sale.vehicle.mapping"].sudo().search([("model", "=", model),("record_id", "ilike", str(rec.uom_id.id)),],limit=1,)
                if mapping_id:
                    uom_number = int(mapping_id[0].key)
            rec.uom_number = uom_number

    @api.onchange("is_next_day")
    def _onchange_next_day(self):
        for rec in self:
            if rec.is_next_day:
                rec.next_day = rec.sale_vehicle_id.date + datetime.timedelta(days=1)
            else:
                rec.next_day = False

    @api.depends("loading")
    def _compute_loading_id(self):
        for rec in self:
            model = "hr.department"
            model_id = self.env[model].sudo()
            if rec.loading:
                exact_match = self.env[model].sudo().search([("name", "=", rec.loading.strip())], limit=1)
                if exact_match:
                    model_id = exact_match
                else:
                    mapping_id = self.env["sale.vehicle.mapping"].sudo().search([("model","=",model),("key","ilike",rec.loading.strip().lower())])
                    if mapping_id:
                        model_id = model_id.browse(int(mapping_id[0].record_id))
            rec.loading_id = model_id

    def _inverse_loading_id(self):
        for rec in self:
            if rec.loading_id:
                rec.loading = rec.loading_id.name

    @api.depends("loading2")
    def _compute_loading2_id(self):
        for rec in self:
            model = "hr.department"
            model_id = self.env[model].sudo()
            if rec.loading2:
                exact_match = self.env[model].sudo().search([("name", "=", rec.loading2.strip())], limit=1)
                if exact_match:
                    model_id = exact_match
                else:
                    mapping_id = self.env["sale.vehicle.mapping"].sudo().search([("model","=",model),("key","ilike",rec.loading2.strip().lower())])
                    if mapping_id:
                        model_id = model_id.browse(int(mapping_id[0].record_id))
            rec.loading2_id = model_id

    def _inverse_loading2_id(self):
        for rec in self:
            if rec.loading2_id:
                rec.loading2 = rec.loading2_id.name

    @api.depends("stocker")
    def _compute_stocker_id(self):
        for rec in self:
            model = "res.users"
            model_id = self.env[model].sudo()
            if rec.stocker:
                exact_match = self.env[model].sudo().search([("name", "=", rec.stocker.strip())], limit=1)
                if exact_match:
                    model_id = exact_match
                else:
                    mapping_id = self.env["sale.vehicle.mapping"].sudo().search([("model", "=", "res.users"), ("key", "ilike", rec.stocker.strip().lower())])
                    if mapping_id:
                        model_id = model_id.browse(int(mapping_id[0].record_id))
            rec.stocker_id = model_id

    def _inverse_stocker_id(self):
        for rec in self:
            if rec.stocker_id:
                rec.stocker = rec.stocker_id.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'weighing_order_id' in vals and vals['weighing_order_id']:
                vals['weighing_history_ids'] = str(vals['weighing_order_id'])
        return super(SaleVehicleInOutLine, self).create(vals_list)

    def write(self, values):
        if 'vehicle_driver' in values:
            if values.get('vehicle_driver') == 'False':
                values['vehicle_driver'] = False
                
        old_order_ids = {rec.id: rec.weighing_order_id.id for rec in self}
        old_so_phieu = {rec.id: rec.weighing_so_phieu for rec in self}

        res = super(SaleVehicleInOutLine, self).write(values)
        
        if not self.env.context.get('skip_history_update') and 'weighing_history_ids' not in values:
            for rec in self:
                trigger_update = False
                if 'weighing_order_id' in values and rec.weighing_order_id.id != old_order_ids.get(rec.id):
                    trigger_update = True
                elif 'weighing_so_phieu' in values and rec.weighing_so_phieu != old_so_phieu.get(rec.id):
                    trigger_update = True
                    
                if trigger_update and rec.weighing_order_id:
                    history = rec.weighing_history_ids
                    if not history:
                        old_id = old_order_ids.get(rec.id)
                        history = str(old_id) if old_id else ""
                        
                    correctName = self.env['stock.weighing.order']._get_weighing_history_correct_name(rec.weighing_order_id.id)
                    
                    new_history = f"{history},{rec.weighing_order_id.id},{correctName}" if history else f"{rec.weighing_order_id.id},{correctName}"
                    rec.with_context(skip_history_update=True).write({'weighing_history_ids': new_history})

        self.env.cr.commit()
        for rec in self:
            if not rec.sale_vehicle_id:
                date = False
                if rec.date_start:
                    date = rec.date_start.date()
                elif rec.date_in:
                    date = rec.date_in.date()
                
                if date:
                    vehicle = self.env["sale.vehicle.in.out"].sudo().search([("date", "=", date)], limit=1)
                    if not vehicle:
                        vehicle = self.env["sale.vehicle.in.out"].sudo().create({
                            "name": "Đăng ký xe ngày %s" % date.strftime("%d/%m/%Y"),
                            "date": date
                        })
                    # Assign the integer ID to avoid Many2one tuple error & infinite recursion
                    rec.with_context(tracking_disable=True).write({"sale_vehicle_id": vehicle.id})
        return res

    def action_create_next_day(self):
        for rec in self:
            next_day = rec.next_day or (
                datetime.date.today() + datetime.timedelta(days=1)
            )
            vehicle = (
                self.env["sale.vehicle.in.out"]
                .sudo()
                .search([("date", "=", next_day)], limit=1)
            )
            if not vehicle:
                vehicle = (
                    self.env["sale.vehicle.in.out"]
                    .sudo()
                    .create(
                        {
                            "name": "Đăng ký xe ngày %s"
                            % next_day.strftime("%d/%m/%Y"),
                            "date": next_day,
                        }
                    )
                )
            new_line_vals = rec.copy_data()[0]
            new_line_vals.update(
                {
                    "sale_vehicle_id": vehicle.id,
                    "date_in": False,
                    "date_start": False,
                    "date_end": False,
                    "is_next_day": False,
                    "is_carried_over": True,
                }
            )
            self.env["sale.vehicle.in.out.line"].sudo().create(new_line_vals)
            rec.has_link_line = True

    @api.model
    def get_vehicle_dashboard_data(self):
        today = fields.Date.context_today(self)
        _logger.info("DASHBOARD: Fetching data for date %s", today)
        
        # You can pass date as param if needed, default to today
        lines = self.search([
            ('sale_vehicle_id.date', '=', today)
        ])
        _logger.info("DASHBOARD: Found %s lines", len(lines))
        
        data = {
            'dang_ky': [],
            'dang_cho': [],
            'xuat_nhap': [],
            'cho_ra': [],
            'hoan_thanh': [],
            'summary': {
                'tong_xe_dang_ky': 0,
                'dang_ky_tong_nhap': 0,
                'dang_ky_tong_xuat': 0,
                'dang_ky_so_xe_nhap': 0,
                'dang_ky_so_xe_xuat': 0,
                'tong_xe_vao': 0,
                'tong_xe_chua_ra': 0,
                'tong_xe_da_ra': 0,
                'tong_xuat': 0,
                'tong_nhap': 0,
                'vao_tong_nhap': 0,
                'vao_tong_xuat': 0,
                'vao_so_xe_nhap': 0,
                'vao_so_xe_xuat': 0,
                'chua_ra_tong_nhap': 0,
                'chua_ra_tong_xuat': 0,
                'chua_ra_so_xe_nhap': 0,
                'chua_ra_so_xe_xuat': 0,
                'da_ra_tong_nhap': 0,
                'da_ra_tong_xuat': 0,
                'da_ra_so_xe_nhap': 0,
                'da_ra_so_xe_xuat': 0,
                'phu_hop': 0,
            }
        }
        
        for line in lines:
            line_data = {
                'id': line.id,
                'type': line.type,
                'vehicle_num': line.vehicle_num or '',
                'partner_name': line.partner_name or '',
                'quantity': f"{line.quantity:.3f}" if line.quantity else "0.000",
                'date_in': fields.Datetime.context_timestamp(self, line.date_in).strftime('%H:%M') if line.date_in else '',
                'chua_du_hang': f"{(line.quantity_plan - line.quantity_done_stock):.3f}" if line.quantity_plan > line.quantity_done_stock else "0.000",
                'du_hang': f"{line.quantity_done_stock:.3f}" if line.quantity_done_stock > 0 else "0.000",
                'gate': line.gate or '',
                'loading': line.loading_id.name if line.loading_id else (line.loading or ''),
                'stocker': line.stocker_id.name if line.stocker_id else (line.stocker or ''),
            }
            
            # Map status
            target_list = None
            if line.canxe_status == 'dang_ky':
                target_list = 'dang_ky'
            elif line.canxe_status == 'chuan_bi':
                target_list = 'dang_cho'
            elif line.canxe_status == 'moi_vao':
                target_list = 'xuat_nhap'
            elif line.canxe_status == 'xuat_nhap':
                target_list = 'cho_ra'
            elif line.canxe_status == 'hoan_thanh':
                # Check invoices for 'cho_ra'
                invoices = self.env['account.move']
                if line.sale_order_ids:
                    invoices |= line.sale_order_ids.mapped('invoice_ids')
                if line.purchase_order_ids:
                    invoices |= line.purchase_order_ids.mapped('invoice_ids')
                    
                valid_invoices = invoices.filtered(lambda inv: inv.state != 'cancel')
                if not valid_invoices:
                    target_list = 'cho_ra'
                else:
                    unpaid_invoices = valid_invoices.filtered(
                        lambda inv: inv.state == 'draft' or inv.payment_state in ('not_paid', 'partial')
                    )
                    if unpaid_invoices:
                        target_list = 'cho_ra'
                    else:
                        target_list = 'hoan_thanh'
                        
            if target_list:
                data[target_list].append(line_data)
                
            # Summaries
            if target_list == 'dang_ky':
                data['summary']['tong_xe_dang_ky'] += 1
                if line.type == 'in':
                    data['summary']['dang_ky_tong_nhap'] += line.quantity or 0
                    data['summary']['dang_ky_so_xe_nhap'] += 1
                if line.type == 'out':
                    data['summary']['dang_ky_tong_xuat'] += line.quantity or 0
                    data['summary']['dang_ky_so_xe_xuat'] += 1
                    
            if target_list and target_list != 'dang_ky':
                data['summary']['tong_xe_vao'] += 1
                if line.type == 'in': 
                    data['summary']['vao_tong_nhap'] += line.quantity or 0
                    data['summary']['vao_so_xe_nhap'] += 1
                if line.type == 'out': 
                    data['summary']['vao_tong_xuat'] += line.quantity or 0
                    data['summary']['vao_so_xe_xuat'] += 1
                
            if target_list == 'cho_ra':
                data['summary']['tong_xe_chua_ra'] += 1
                if line.type == 'in': 
                    data['summary']['chua_ra_tong_nhap'] += line.quantity or 0
                    data['summary']['chua_ra_so_xe_nhap'] += 1
                if line.type == 'out': 
                    data['summary']['chua_ra_tong_xuat'] += line.quantity or 0
                    data['summary']['chua_ra_so_xe_xuat'] += 1
                
            if target_list == 'hoan_thanh':
                data['summary']['tong_xe_da_ra'] += 1
                if line.type == 'in': 
                    data['summary']['da_ra_tong_nhap'] += line.quantity or 0
                    data['summary']['da_ra_so_xe_nhap'] += 1
                if line.type == 'out': 
                    data['summary']['da_ra_tong_xuat'] += line.quantity or 0
                    data['summary']['da_ra_so_xe_xuat'] += 1
                
            if line.type == 'out':
                data['summary']['tong_xuat'] += line.quantity or 0
            elif line.type == 'in':
                data['summary']['tong_nhap'] += line.quantity or 0

        # Calculate percentage (example logic)
        if data['summary']['tong_xe_vao'] > 0:
            data['summary']['phu_hop'] = round((data['summary']['tong_xe_da_ra'] / data['summary']['tong_xe_vao']) * 100, 1)
            
        return data
