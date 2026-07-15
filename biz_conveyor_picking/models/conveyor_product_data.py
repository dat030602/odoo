from odoo import models, fields, api

class ConveyorProductData(models.Model):
    _name = 'conveyor.product.data'
    _description = 'Dữ liệu sản phẩm băng tải'
    _order = 'create_date desc'

    # Liên kết với conveyor.data
    conveyor_data_id = fields.Many2one('conveyor.data', string='Dữ liệu băng tải', required=True, ondelete='cascade')
    
    # Các trường từ API Product array
    pro_code = fields.Char('Mã sản phẩm', required=True, help='Mã Sản Phẩm')
    pro_name = fields.Char('Tên sản phẩm', required=True, help='Tên Sản Phẩm')
    mo_plan_num = fields.Float('Số lượng kế hoạch', required=True, help='Số Lượng Kế Hoạch Cần Lấy')
    mo_real_num = fields.Float('Số lượng thực đếm', help='Số Lượng Thực Đếm')
    mo_start_num = fields.Float('Số lượng bắt đầu đếm', help='Số Lượng Bắt Đầu Đếm')
    
    # Các trường từ array index (0, 1, 2, 3, 4)
    index_0 = fields.Char('Index 0', help='Giá trị index 0 từ API')
    index_1 = fields.Char('Index 1', help='Giá trị index 1 từ API')
    index_2 = fields.Char('Index 2', help='Giá trị index 2 từ API')
    index_3 = fields.Char('Index 3', help='Giá trị index 3 từ API')
    index_4 = fields.Char('Index 4', help='Giá trị index 4 từ API')
    
    # Trường tính toán
    difference = fields.Float('Chênh lệch', compute='_compute_difference', store=True)
    completion_rate = fields.Float('Tỷ lệ hoàn thành (%)', compute='_compute_completion_rate', store=True)
    
    # Trường liên kết với sản phẩm Odoo
    product_id = fields.Many2one('product.product', string='Sản phẩm Odoo', 
                                domain=[('type', 'in', ['product', 'consu'])])
    
    @api.depends('mo_plan_num', 'mo_real_num')
    def _compute_difference(self):
        for record in self:
            if record.mo_plan_num and record.mo_real_num:
                record.difference = record.mo_real_num - record.mo_plan_num
            else:
                record.difference = 0.0

    @api.depends('mo_plan_num', 'mo_real_num')
    def _compute_completion_rate(self):
        for record in self:
            if record.mo_plan_num and record.mo_real_num:
                record.completion_rate = (record.mo_real_num / record.mo_plan_num)
            else:
                record.completion_rate = 0.0

    @api.model
    def create(self, vals):
        # Tự động tìm product_id dựa trên pro_code
        if vals.get('pro_name') and not vals.get('product_id'):
            product = self.env['product.product'].search([
                ('default_code', '=', vals['pro_name'])
            ], limit=1)
            if product:
                vals['product_id'] = product.id
        return super(ConveyorProductData, self).create(vals)

    def action_view_product(self):
        """Mở sản phẩm liên quan"""
        self.ensure_one()
        if self.product_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sản phẩm',
                'res_model': 'product.product',
                'res_id': self.product_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return True 