from odoo import models, fields, api, _

class StockMoveWizardLine(models.TransientModel):
    _name = 'stock.move.wizard.line'
    _description = 'Dòng Wizard cho Phiếu Điều Chuyển Kho'
    
    wizard_id = fields.Many2one('stock.move.wizard', string="Wizard")
    purchase_line_id = fields.Many2one('purchase.order.line', string="Dòng Đơn Mua",)
    product_id = fields.Many2one('product.product', string="Sản Phẩm",)
    
    # Các trường này giờ đây được điền giá trị bởi default_get, không cần compute
    delivered_qty = fields.Float(string="Số Lượng Đã Giao")
    invoiced_qty = fields.Float(string="Số Lượng Đã Lập Hóa Đơn")
    diff_qty = fields.Float(string="Số Lượng Chênh Lệch",digits="Product Unit of Measure")
    
    # Cho phép người dùng chỉnh sửa tài khoản nếu cần
    credit_account_id = fields.Many2one('account.account', string="Tài Khoản Có")
    debit_account_id = fields.Many2one('account.account', string="Tài Khoản Nợ")
    
    location_id = fields.Many2one('stock.location', string="Vị trí",)
    currency_id = fields.Many2one('res.currency', string="Tiền tệ", related="purchase_line_id.currency_id")
    
    price_unit = fields.Monetary(string="Đơn giá")
    price_total = fields.Monetary(string="Tổng giá trị")
    
    type = fields.Selection(string="Loại", selection=[
        ('extra','Thừa'),
        ('lack','Thiếu'),
    ],default="extra", required=True)
    
    @api.onchange('diff_qty','type')
    def _onchange_diff_qty(self):
        for rec in self:
            rec.price_total = rec.price_unit * abs(rec.diff_qty)
            if rec.location_id:
                credit_account_id = False
                debit_account_id = False
                if rec.type == 'extra':  # Thừa hàng -> Nhập kho
                    credit_account_id = rec.location_id.valuation_out_account_id.id
                    debit_account_id = rec.product_id.categ_id.property_stock_valuation_account_id.id
                else:  # Thiếu hàng -> Xuất kho
                    credit_account_id = rec.product_id.categ_id.property_stock_valuation_account_id.id
                    debit_account_id = rec.location_id.valuation_in_account_id.id
                rec.credit_account_id = credit_account_id
                rec.debit_account_id = debit_account_id
