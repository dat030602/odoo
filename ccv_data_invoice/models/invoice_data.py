from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import unidecode
from rapidfuzz import process
import logging

_logger = logging.getLogger(__name__)

def normalize_name(name):
    """Chuẩn hóa tên sản phẩm (lowercase, bỏ dấu, chuẩn ký tự phân cách)."""
    if not name:
        return ""
    name = name.lower()
    name = unidecode.unidecode(name)  # bỏ dấu
    name = re.sub(r'[\s\*xX\-]+', 'x', name)  # chuẩn hóa x/*/-
    name = re.sub(r'\s+', ' ', name).strip()
    return name

class InvoiceDataMisa(models.Model):
    _name = 'invoice.data'
    _description = 'Dữ liệu hóa đơn'
    _rec_name = 'so_hoa_don'
    _order = 'ngay_lap desc'

    # Thông tin chung hóa đơn
    so_hoa_don = fields.Char(string='Số hóa đơn', required=True, index=True)
    ky_hieu = fields.Char(string='Ký hiệu hóa đơn', required=True)
    ngay_lap = fields.Date(string='Ngày lập hóa đơn', required=True, index=True)
    
    # Thông tin người bán
    nban_ten = fields.Char(string='Tên người bán')
    nban_id = fields.Many2one('res.partner', string='Người bán', compute='_compute_nban_id', store=True)
    nban_mst = fields.Char(string='Mã số thuế người bán')
    nban_dia_chi = fields.Text(string='Địa chỉ người bán')
    nban_dt_cong_no = fields.Many2one('res.partner', string='Đối tượng công nợ', compute='_compute_nban_id', store=True)
    
    # Thông tin người mua
    nmua_ten = fields.Char(string='Tên người mua')
    nmua_id = fields.Many2one('res.partner', string='Người mua', compute='_compute_nmua_id', store=True)
    nmua_mst = fields.Char(string='Mã số thuế người mua')
    nmua_dia_chi = fields.Text(string='Địa chỉ người mua')

    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], string='Loại hiển thị', default='line_section')
    
    # Tổng tiền
    tong_tien = fields.Float(string='Tổng tiền thanh toán', digits=(16, 2))
    currency_id = fields.Many2one('res.currency', string='Loại tiền', default=lambda self: self.env.company.currency_id)
    
    # Danh sách hàng hóa dịch vụ
    ds_hhdv_ids = fields.One2many('invoice.data.line', 'invoice_id', string='Danh sách hàng hóa dịch vụ')
    
    # Danh sách hàng hóa dịch vụ với trường m2o
    ds_hhdv_m2o_ids = fields.One2many('invoice.data.line.m2o', 'invoice_id', string='Danh sách hàng hóa dịch vụ (M2O)')
    
    # Trường lưu thông tin hóa đơn đã tạo
    created_invoice_ids = fields.Many2many('account.move', string='Hóa đơn đã tạo', readonly=True)
    created_invoice_count = fields.Integer(string='Số hóa đơn đã tạo', compute='_compute_created_invoice_count', store=True)
    
    # Trường tính toán
    tong_so_luong = fields.Float(string='Tổng số lượng', compute='_compute_tong_so_luong', store=True)
    tong_thanh_tien = fields.Float(string='Tổng thành tiền', compute='_compute_tong_thanh_tien', store=True)

    # Trường lưu thông tin đơn đặt hàng
    purchase_order_ids = fields.Many2many('purchase.order', string='Đơn đặt hàng')
    picking_ids = fields.Many2many('stock.picking', 'invoice_data_stock_picking_rel', 'invoice_data_id', 'stock_picking_id', string='Điều chuyển')
    
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đang xử lí'),
        ('processed', 'Đã tạo hóa đơn'),
        ('done', 'Đã vào sổ'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='draft', compute='_compute_state', store=True)
    
    # Ghi chú
    notes = fields.Text(string='Ghi chú')
    
    # Ngày tạo và cập nhật
    create_date = fields.Datetime(string='Ngày tạo', readonly=True)
    write_date = fields.Datetime(string='Ngày cập nhật', readonly=True)

    @api.depends('created_invoice_ids.state', 'created_invoice_ids', 'ds_hhdv_m2o_ids')
    def _compute_state(self):
        for record in self:
            if record.created_invoice_ids:
                if all(invoice.state == 'posted' for invoice in record.created_invoice_ids):
                    record.state = 'done'
                elif all(invoice.state == 'cancel' for invoice in record.created_invoice_ids):
                    record.state = 'cancelled'
                elif any(invoice.state != 'cancel' for invoice in record.created_invoice_ids):
                    record.state = 'processed'
                else:
                    record.state = 'confirmed'
            elif record.ds_hhdv_m2o_ids:
                record.state = 'confirmed'
            else:
                record.state = 'draft'

    @api.depends('nban_mst')
    def _compute_nban_id(self):
        """Tự động gán người bán dựa trên mã số thuế"""
        for record in self:
            if record.nban_mst:
                partner = self.env['res.partner'].search([
                    ('vat', '=', record.nban_mst)
                ], limit=1)
                record.nban_id = partner.id if partner else False
                record.nban_dt_cong_no = partner.id if partner else False
            else:
                record.nban_id = False
                record.nban_dt_cong_no = False
                
    @api.depends('nmua_mst')
    def _compute_nmua_id(self):
        """Tự động gán người mua dựa trên mã số thuế"""
        for record in self:
            if record.nmua_mst:
                partner = self.env['res.partner'].search([
                    ('vat', '=', record.nmua_mst)
                ], limit=1)
                record.nmua_id = partner.id if partner else False
            else:
                record.nmua_id = False
    
    @api.depends('ds_hhdv_ids.so_luong')
    def _compute_tong_so_luong(self):
        for record in self:
            record.tong_so_luong = sum(record.ds_hhdv_ids.mapped('so_luong'))
    
    @api.depends('ds_hhdv_ids.thanh_tien')
    def _compute_tong_thanh_tien(self):
        for record in self:
            record.tong_thanh_tien = sum(record.ds_hhdv_ids.mapped('thanh_tien'))

    def fuzzy_find_product(self, supplier_name, threshold=80):
        """
        Tìm sản phẩm gần đúng theo tên NCC (fuzzy search).
        :param supplier_name: tên sản phẩm từ NCC (str)
        :param threshold: ngưỡng khớp tối thiểu (0-100)
        :return: record product.product hoặc None
        """
        supplier_norm = normalize_name(supplier_name)

        # Lấy danh sách sản phẩm từ Odoo
        products = self.env['product.product'].search([])  # bạn có thể thêm domain để lọc
        product_names = {normalize_name(p.name): p.id for p in products}

        # Fuzzy search với RapidFuzz
        match = process.extractOne(
            supplier_norm, 
            product_names.keys()
        )

        if match:
            matched_name, score, _ = match
            if score >= threshold:
                return self.env['product.product'].browse(product_names[matched_name])
        return None

    def action_create_partner(self):
        self.ensure_one()
        partner = self.env['res.partner'].search([
            ('vat', '=', self.nban_mst)
        ], limit=1)
        if partner:
            self._compute_nban_id()
        else:
            default_vals = {
                'company_type': 'company',
                'vat': self.nban_mst or '',
                'name': self.nban_ten or '',
                'street': self.nban_dia_chi or '',
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tạo đối tác',
                'view_mode': 'form',
                'res_model': 'res.partner',
                'target': 'new',
                'context': {**self.env.context, **{'default_%s' % k: v for k, v in default_vals.items()}},
                'res_id': False,
                'views': [[self.env.ref('base.view_partner_form').id, 'form']],
            }
    
    def action_compute_m2o_lines(self):
        """Tính toán và tạo dữ liệu cho bảng M2O từ dữ liệu gốc"""
        env_mapping = self.env['mapping.data.product']
        for record in self:
            _logger.info(f"Bắt đầu tính toán M2O cho hóa đơn: {record.so_hoa_don}")
            
            # Xóa dữ liệu cũ trong bảng M2O
            old_lines = record.ds_hhdv_m2o_ids
            if old_lines:
                old_lines.unlink()
            
            # Xử lý từng dòng trong ds_hhdv_ids
            for line in record.ds_hhdv_ids:
                _logger.info(f"Xử lý dòng: {line.ten}")
                product_name_lower = line.ten.lower()
                selected_product = self.env['product.product']
                account_id = self.env['account.account']

                # Phí, cont, trọng lượng, cân
                mapping_products = env_mapping.search([('active', '=', True)])
                for mapping in mapping_products:
                    if mapping.keyword:
                        keywords = [kw.strip().lower() for kw in mapping.keyword.split(',')]
                        for keyword in keywords:
                            if keyword and keyword in product_name_lower:
                                if mapping.product_id:
                                    selected_product = mapping.product_id
                                    account_id = mapping.account_id
                                    break
                        if selected_product:
                            break
                if not selected_product:
                    selected_product = self.fuzzy_find_product(line.ten)

                selected_uom = self.env['uom.uom']
                if line.dvt:
                    selected_uom = self.env['uom.uom'].search([('name', '=', line.dvt)], limit=1)
                    if not selected_uom:
                        selected_uom = self.env['uom.uom'].search([('name', 'ilike', line.dvt)], limit=1)
                
                selected_tax = self.env['account.tax']
                if line.thue_suat:
                    try:
                        tax_rate = float(line.thue_suat.replace('%', ''))
                        selected_tax = selected_tax.search([('amount', '=', tax_rate),('type_tax_use', '=', 'purchase'),('name', 'ilike', 'GTGT')], limit=1)
                        if not selected_tax:
                            selected_tax = selected_tax.search([('amount', '=', tax_rate), ('type_tax_use', '=', 'purchase')], limit=1)
                    except (ValueError, AttributeError):
                        pass

                # Tạo ghi chú theo cấu trúc yêu cầu
                ghi_chu_formatted = ""
                if record.nmua_ten and record.so_hoa_don and line.ten:
                    ghi_chu_formatted = "Chi phí phải trả {nban_ten}, {ten}: số lượng {so_luong} {dvt}, theo HĐ số {so_hoa_don}"
                    ghi_chu_formatted = ghi_chu_formatted.format(
                        nban_ten=record.nban_ten,
                        ten=line.ten,
                        dvt=line.dvt or 'kg',
                        so_luong=line.so_luong,
                        so_hoa_don=record.so_hoa_don
                    )
                
                # Tạo bản ghi mới trong bảng M2O
                if not selected_product:
                    mapping_products = env_mapping.search([('create_auto', '=', True)], limit=1)
                    selected_product = mapping_products[0].product_id if mapping_products else False
                if not account_id and selected_product:
                    account_id = selected_product._get_product_accounts().get('expense', False) if selected_product._get_product_accounts().get('expense', False) else False
                vals = {
                    'invoice_id': record.id,
                    'sequence': line.sequence,
                    'product_id': selected_product.id if selected_product else False,
                    'product_name': line.ten,
                    'uom_id': selected_uom.id if selected_uom else selected_product.uom_id.id,
                    'so_luong': line.so_luong,
                    'don_gia': line.don_gia,
                    'thanh_tien': line.thanh_tien,
                    'tax_id': selected_tax.id if selected_tax else False,
                    'ghi_chu': ghi_chu_formatted or f"Tự động tạo từ: {line.ten}",
                    'source_line_id': line.id,
                    'account_id': account_id.id if account_id else False,
                }
                
                new_line = self.env['invoice.data.line.m2o'].create(vals)
                # new_line._onchange_product_id()
                new_line._onchange_tax_id()
                new_line._onchange_thanh_tien()
        return True
    
    @api.depends('so_hoa_don', 'ky_hieu')
    def _compute_created_invoice_count(self):
        for record in self:
            record.created_invoice_count = self.env['account.move'].search_count([('ref', '=', record.so_hoa_don), ('series', '=', record.ky_hieu)])
    
    @api.constrains('so_hoa_don', 'ky_hieu','nban_mst')
    def _check_so_hoa_don_unique(self):
        for record in self:
            if record.so_hoa_don and record.ky_hieu:
                duplicate = self.search([
                    ('so_hoa_don', '=', record.so_hoa_don),
                    ('ky_hieu', '=', record.ky_hieu),
                    ('nban_mst', '=', record.nban_mst),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(_('Hóa đơn với số %s, ký hiệu %s và mã số thuế %s đã tồn tại!') % 
                                        (record.so_hoa_don, record.ky_hieu, record.nban_mst))
    
    def name_get(self):
        """Hiển thị tên hóa đơn"""
        result = []
        for record in self:
            name = f"{record.ky_hieu} - {record.so_hoa_don}"
            if record.nban_ten:
                name += f" - {record.nban_ten}"
            if record.nban_mst:
                name += f" - {record.nban_mst}"
            result.append((record.id, name))
        return result

    def action_view_purchase_order(self):
        self.ensure_one()
        action = self.env.ref('purchase.purchase_rfq').sudo().read()[0]
        if len(self.purchase_order_ids) == 1:
            action['res_id'] = self.purchase_order_ids.id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
        else:
            action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        return action

    def action_create_invoice(self):
        """Tạo hóa đơn nhà cung cấp từ dữ liệu hiện có"""
        for record in self:
            _logger.info(f"Bắt đầu tạo hóa đơn nhà cung cấp cho: {record.so_hoa_don}")
            
            # Kiểm tra dữ liệu cần thiết
            if not record.ds_hhdv_m2o_ids:
                raise ValidationError(_('Vui lòng tính toán M2O trước khi tạo hóa đơn!'))
            
            if not record.nban_id:
                raise ValidationError(_('Vui lòng chọn người bán trước khi tạo hóa đơn!'))
            
            # Tạo wizard để chọn dòng cần tạo hóa đơn
            line_ids = []
            for line in record.ds_hhdv_m2o_ids:
                qty = line.so_luong
                
                # Tìm purchase order line tương ứng với sản phẩm
                for purchase_order in record.purchase_order_ids:
                    for po_line in purchase_order.order_line.filtered(lambda l: l.product_id == line.product_id):
                        quantity = po_line.product_qty - po_line.qty_invoiced
                        if quantity <= 0:
                            continue
                        val = {
                            'sequence': line.sequence,
                            'product_id': line.product_id.id,
                            'uom_id': line.uom_id.id,
                            'account_id': line.account_id.id,
                            'so_luong': qty,
                            'don_gia': line.don_gia,
                            'thanh_tien': line.thanh_tien,
                            'tax_id': line.tax_id.id,
                            'thue_gtgt': line.thue_gtgt,
                            'ghi_chu': line.ghi_chu,
                            'invoice_data_line_id': line.id,
                            'is_selected': True,
                        }
                        val['purchase_line_id'] = po_line.id
                        val['so_luong'] = min(qty, quantity)
                        val['thanh_tien'] = val['so_luong'] * val['don_gia']
                        line_ids.append((0, 0, val))
                        qty -= val['so_luong']
                        if qty <= 0:
                            break
                if qty > 0:
                    val = {
                        'sequence': line.sequence,
                        'product_id': line.product_id.id,
                        'uom_id': line.uom_id.id,
                        'account_id': line.account_id.id,
                        'so_luong': qty,
                        'don_gia': line.don_gia,
                        'thanh_tien': line.thanh_tien,
                        'tax_id': line.tax_id.id,
                        'thue_gtgt': line.thue_gtgt,
                        'ghi_chu': line.ghi_chu,
                        'invoice_data_line_id': line.id,
                        'is_selected': True,
                    }
                    line_ids.append((0, 0, val))
                        
            return {
                'name': _('Chọn sản phẩm để tạo hóa đơn'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'wz.invoice.data.create.invoice',
                'target': 'new',
                'context': {
                    'default_invoice_data_id': record.id,
                    'default_order_line': line_ids
                }
            }

    def create_data_mapping_product(self):
        data_mapping = []
        env_mapping = self.env['mapping.data.product']
        for m2o_line in self.ds_hhdv_m2o_ids:
            # Kiểm tra xem keyword đã tồn tại trong mapping chưa, nếu có thì bỏ qua
            if env_mapping.search_count([('keyword', '=', m2o_line.source_line_id.ten)]):
                continue
            vals = {
                'keyword': m2o_line.source_line_id.ten,
                'product_id': m2o_line.product_id.id,
                'account_id': m2o_line.account_id.id,
                'active': True,
                'create_auto': True,
            }
            data_mapping.append(vals)
        mapping_product = env_mapping.create(data_mapping)
    
    def action_done_create_invoice(self, lines):
        """Thực hiện tạo hóa đơn nhà cung cấp"""
        self.ensure_one()
        
        _logger.info(f"Thực hiện tạo hóa đơn nhà cung cấp cho {len(lines)} dòng")
        
        # Chuẩn bị dữ liệu hóa đơn
        invoice_vals = {
            'move_type': 'in_invoice',  # Hóa đơn nhà cung cấp
            'partner_id': self.nban_id.id,
            'invoice_date': self.ngay_lap,
            'ref': self.so_hoa_don,
            'series': self.ky_hieu,
            'note': self.notes,
            'purchase_ids': [(6, 0, self.purchase_order_ids.ids)],
            # 'payment_reference': self.so_hoa_don,
            'company_id': self.env.company.id,
            'currency_id': self.env.company.currency_id.id,
            'invoice_line_ids': [],
            'invoice_data_ids': [(4, self.id)],
        }
        
        # Thêm các dòng hóa đơn
        sequence = 10
        for line in lines:
            if not line.product_id:
                _logger.warning(f"Bỏ qua dòng {line.id} - không có sản phẩm")
                continue
                
            line_vals = {
                'sequence': sequence,
                'purchase_line_id': line.purchase_line_id.id,
                'product_id': line.product_id.id,
                'name': line.ghi_chu,
                'invoice_code': self.ky_hieu,
                'date_invoice': self.ngay_lap,
                'invoice_number':'/' + self.so_hoa_don,
                'product_uom_id': line.uom_id.id or False,
                'quantity': line.so_luong,
                'price_unit': line.don_gia,
                'tax_ids': [(6, 0, [line.tax_id.id])] if line.tax_id else [],
                'account_id': line.account_id.id if line.account_id else line.product_id.categ_id.property_account_expense_categ_id.id,
            }
            
            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
            sequence += 10
            _logger.info(f"Thêm dòng hóa đơn: {line.product_id.name} - SL: {line.so_luong} - ĐG: {line.don_gia}")
        
        if not invoice_vals['invoice_line_ids']:
            raise ValidationError(_('Không có dòng nào hợp lệ để tạo hóa đơn!'))
        
        # Tạo hóa đơn
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        invoice = AccountMove.create(invoice_vals)
        body = "%s được tạo từ %s" % (self._description, self._get_html_link())
        invoice.message_post(body=body)
        
        _logger.info(f"Đã tạo hóa đơn nhà cung cấp: {invoice.name}")

        line_ids = invoice.line_ids.filtered(lambda l: l.account_id.account_type != 'liability_payable')
        if self.nban_dt_cong_no != self.nban_id:
            invoice.partner_id = self.nban_dt_cong_no
            if line_ids:
                line_ids.write({'partner_id': self.nban_id.id})
        
        # Thêm hóa đơn vào danh sách đã tạo
        self.created_invoice_ids |= invoice
        
        # Cập nhật lại số lượng hóa đơn đã tạo
        self._compute_created_invoice_count()
        
        # Hiển thị thông báo thành công và mở hóa đơn
        return {
            'type': 'ir.actions.act_window',
            'name': _('Hóa đơn nhà cung cấp'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_created_invoices(self):
        """Mở danh sách hóa đơn đã tạo"""
        self.ensure_one()
        
        if not self.created_invoice_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': 'Chưa có hóa đơn nào được tạo từ hóa đơn điện tử này',
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        # Mở danh sách hóa đơn đã tạo
        if len(self.created_invoice_ids) == 1:
            # Nếu chỉ có 1 hóa đơn thì mở trực tiếp
            return {
                'type': 'ir.actions.act_window',
                'name': _('Hóa đơn đã tạo'),
                'res_model': 'account.move',
                'res_id': self.created_invoice_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Nếu có nhiều hóa đơn thì hiển thị danh sách
            return {
                'type': 'ir.actions.act_window',
                'name': _('Hóa đơn đã tạo'),
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.created_invoice_ids.ids)],
                'context': {'default_move_type': 'in_invoice'},
                'target': 'current',
            }
    
    def action_open_picking(self):
        action = self.env.ref("stock.action_picking_tree_all").sudo().read()[0]
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action
