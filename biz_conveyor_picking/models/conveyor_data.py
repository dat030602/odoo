from odoo import models, fields, api

class ConveyorData(models.Model):
    _name = 'conveyor.data'
    _description = 'Dữ liệu băng tải'
    _rec_name = 'mo_code_odoo'
    _order = 'create_date desc'

    # Các trường bắt buộc (Required = Yes)
    mo_code_odoo = fields.Char('Mã đơn hàng Odoo', required=True, help='Mã đơn hàng từ Odoo gửi xuống bộ đếm')

    # Các trường không bắt buộc (Required = No)
    mo_customer = fields.Char('Tên khách hàng', help='Tên Khách Hàng')
    mo_tranz = fields.Char('Tên phương tiện', help='Tên Phương Tiện (Biển Số Xe)')
    mo_start_time = fields.Char('Thời gian bắt đầu', help='Thời gian bắt đầu 1 đơn hàng')
    mo_close_time = fields.Char('Thời gian kết thúc', help='Thời gian kết thúc 1 đơn hàng')
    mo_note = fields.Text('Ghi chú', help='Ghi chú thêm từ API response')

    # Trường từ API response
    queue = fields.Integer('Queue', help='Queue number từ API response')

    # Trường liên kết với đơn hàng
    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập/xuất kho', 
                                domain=[('state', 'in', ['confirmed', 'assigned', 'done'])])

    sale_order_id = fields.Many2one('sale.order', string='Đơn hàng', related='picking_id.sale_id')
    # Trường liên kết với dữ liệu sản phẩm
    product_data_ids = fields.One2many('conveyor.product.data', 'conveyor_data_id', string='Dữ liệu sản phẩm')
    
    def get_vehicle_in_out_data(self):
        """
        Lấy dữ liệu liên quan đến sale.vehicle.in.out dựa trên mo_start_time (định dạng ngày) và mo_tranz (biển số xe).
        Trả về dict gồm: data_start, date_end, sale_vehicle_in_out, sale_vehicle_in_out_line (nếu tìm thấy).
        """
        # Chuyển đổi mo_start_time và mo_close_time sang kiểu date
        from datetime import datetime, timedelta

        def parse_date(date_str):
            # Thử các định dạng phổ biến
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except Exception:
                    continue
            return False

        def parse_datetime(datetime_str):
            # Thử các định dạng phổ biến cho datetime
            from datetime import datetime
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    return datetime.strptime(datetime_str, fmt)
                except Exception:
                    continue
            return False

        data = parse_date(self.mo_start_time) if self.mo_start_time else False
        date_start = parse_datetime(self.mo_start_time) if self.mo_start_time else False
        date_end = parse_datetime(self.mo_close_time) if self.mo_close_time else False
        

        sale_vehicle_in_out = False

        if date_start and self.mo_tranz:
            # Tìm sale.vehicle.in.out có date = data_start
            sale_vehicle_in_out = self.env['sale.vehicle.in.out'].search([('date', '=', data)], limit=1)
            if sale_vehicle_in_out:
                # Tìm line có vehicle_num = mo_tranz
                line = sale_vehicle_in_out.line_ids.filtered(lambda l: l.vehicle_num == self.mo_tranz)
                if line and line.date_start and line.date_end:
                    if line and date_start and (date_start - timedelta(hours=7)) <= line.date_start:
                        line.write({'date_start': (date_start - timedelta(hours=7))})
                    elif line and date_end and (date_end - timedelta(hours=7)) > line.date_end:
                        line.write({'date_end': (date_end - timedelta(hours=7))})
                else:
                    if date_start:
                        line.write({'date_start': (date_start - timedelta(hours=7))})
                    if date_end:
                        line.write({'date_end': (date_end - timedelta(hours=7))})
                    
                
    @api.model
    def create(self, vals):
        # Tự động tìm picking_id dựa trên mo_code_odoo
        if vals.get('mo_code_odoo') and not vals.get('picking_id'):
            picking = self.env['stock.picking'].search([
                ('name', '=', vals['mo_code_odoo'])
            ], limit=1)
            if picking:
                vals['picking_id'] = picking.id
        res = super(ConveyorData, self).create(vals)
        res.get_vehicle_in_out_data()
        return res


    @api.depends('product_data_ids.product_id')
    def _compute_product_ids(self):
        for record in self:
            product_ids = record.product_data_ids.mapped('product_id').ids
            record.product_ids = [(6, 0, product_ids)]

    product_ids = fields.Many2many(
        'product.product',
        string='Sản phẩm',
        compute='_compute_product_ids',
        store=True,
        help='Danh sách sản phẩm lấy từ các dòng dữ liệu sản phẩm'
    )

    def action_view_picking(self):
        """Mở phiếu nhập/xuất kho liên quan"""
        self.ensure_one()
        if self.picking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Phiếu nhập/xuất kho',
                'res_model': 'stock.picking',
                'res_id': self.picking_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return True

    def action_view_products(self):
        """Mở danh sách sản phẩm liên quan"""
        self.ensure_one()
        if self.product_data_ids:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Dữ liệu sản phẩm',
                'res_model': 'conveyor.product.data',
                'view_mode': 'tree,form',
                'domain': [('conveyor_data_id', '=', self.id)],
                'target': 'current',
            }
        return True 