from odoo import models, fields, api, _

class InvoiceMisaStockWizardLine(models.TransientModel):
    _name = 'invoice.misa.stock.wizard.line'
    _description = 'Dòng Wizard cho Phiếu Điều Chuyển Kho'
    
    wizard_id = fields.Many2one('invoice.misa.stock.wizard', string="Wizard")
    purchase_line_id = fields.Many2one('purchase.order.line', string="Dòng Đơn Mua")
    product_id = fields.Many2one('product.product', string="Sản Phẩm",)
    
    # Các trường này giờ đây được điền giá trị bởi default_get, không cần compute
    quantity = fields.Float(string="Số Lượng",digits="Product Unit of Measure")
    price_unit = fields.Float(string="Đơn giá", digits="Product Price")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)
