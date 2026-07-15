from odoo import models, fields, api

class SalarySalesSummaryDetailLine(models.Model):
    """Unified detail line model for revenue, payment, and invoice details"""
    _name = 'salary.sales.summary.detail.line'
    _description = 'Salary Sales Summary Detail Line'

    name = fields.Char(string='Tên', related='summary_line_id.name')
    summary_line_id = fields.Many2one('salary.sales.summary.line', string='Dòng tổng hợp', required=True, ondelete='cascade')
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', related='summary_line_id.summary_id', store=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', related='summary_line_id.team_id', store=True)
    state_id = fields.Many2one('res.country.state', string='Tỉnh', related='summary_line_id.state_id', store=True)
    active = fields.Boolean(string='Kích hoạt', related='summary_line_id.active')
    
    # Loại dòng: revenue, payment, invoice
    line_type = fields.Selection([
        ('revenue', 'Chi tiết doanh thu'),
        ('payment', 'Chi tiết doanh thu tiền về'),
        ('invoice', 'Chi tiết xuất hóa đơn trước')
    ], string='Loại dòng', required=True, default='revenue')
    
    # Common fields for all line types
    sale_order_ids = fields.Many2many(
        'sale.order', 
        'sale_order_salary_sales_summary_detail_line_rel',
        'detail_line_id',
        'sale_order_id',
        string='Đơn hàng'
    )
    partner_id = fields.Many2one('res.partner', string='Khách hàng', related='sale_order_ids.partner_id', store=True)
    is_first_order = fields.Selection(string='Đơn hàng đầu tiên của Khách hàng?', related='sale_order_ids.x_studio_n_hng_u_tin_ca_khch_hng', store=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    
    # Revenue and Invoice specific fields
    delivery_date = fields.Date(string='Ngày giao')
    invoice_date = fields.Date(string='Ngày xuất hóa đơn')
    quantity = fields.Float(string='Số lượng', digits="Product Unit of Measure")
    unit_price = fields.Monetary(string='Đơn giá')
    amount_untaxed = fields.Monetary(string='Thành tiền trước thuế')
    amount_total = fields.Monetary(string='Thành tiền sau thuế')
    amount_tax = fields.Monetary(string='Tiền thuế')
    
    # Payment `specific fields
    communication = fields.Char(string='Diễn giải giao dịch')
    amount = fields.Monetary(string='Số tiền')
    payment_date = fields.Date(string='Ngày')
    payment_id = fields.Many2one('account.payment', string='Phiếu thanh toán')
    
    # Invoice fields (for both invoice lines and payment lines)
    invoice_ids = fields.Many2many(
        'account.move',
        'account_move_salary_sales_summary_detail_line_rel',
        'detail_line_id',
        'account_move_id',
        string='Hóa đơn'
    )
    invoice_vat_sinvoice_number = fields.Char(string='Mã hóa đơn', compute='_compute_invoice_vat_sinvoice_number', store=True)

    amount_pre_inv = fields.Monetary(string='Số tiền chưa trả')
    
    # Computed total amount field
    total_amount = fields.Monetary(string='Tổng tiền', compute='_compute_total_amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('invoice_ids.vat_sinvoice_number')
    def _compute_invoice_vat_sinvoice_number(self):
        for record in self:
            record.invoice_vat_sinvoice_number = ', '.join(str(vat_inv) for vat_inv in record.invoice_ids.mapped('vat_sinvoice_number') if vat_inv)
    
    @api.depends('amount_total', 'amount', 'line_type')
    def _compute_total_amount(self):
        for record in self:
            if record.line_type == 'payment':
                record.total_amount = record.amount
            else:
                record.total_amount = record.amount_total
    
    def action_view_sale_order(self):
        """Action để xem chi tiết đơn hàng"""
        self.ensure_one()
        if not self.sale_order_ids:
            return False
        if len(self.sale_order_ids) > 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Đơn hàng',
                'res_model': 'sale.order',
                'res_ids': self.sale_order_ids.ids,
                'view_mode': 'tree',
                'target': 'current',
            }
        elif len(self.sale_order_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Đơn hàng',
                'res_model': 'sale.order',
                'res_id': self.sale_order_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def action_view_payment(self):
        """Action để xem chi tiết phiếu thanh toán"""
        self.ensure_one()
        if not self.payment_id:
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phiếu thanh toán',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_invoice(self):
        """Action để xem chi tiết hóa đơn"""
        self.ensure_one()
        if not self.invoice_ids:
            return False
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(self.invoice_ids) > 1:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
            return action
        elif len(self.invoice_ids) == 1:
            action['res_id'] = self.invoice_ids.id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
            return action
