from odoo import models, fields, api

class SalarySalesSummaryLine(models.Model):
    """Main line model containing all summary fields"""
    _name = 'salary.sales.summary.line'
    _description = 'Salary Sales Summary Line'

    name = fields.Char(string='Tên', related='team_id.report_name')
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    state_id = fields.Many2one(string='Tỉnh', comodel_name='res.country.state')
    team_id = fields.Many2one(string='Khu vực', comodel_name='crm.team')
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    
    # Sản lượng
    production_quantity = fields.Float(string='Sản lượng', digits="Product Unit of Measure", compute='_compute_total_revenue', store=True)
    
    # Doanh thu - Chi tiết đơn hàng
    detail_line_ids = fields.One2many(
        string='Chi tiết', 
        comodel_name='salary.sales.summary.detail.line', 
        inverse_name='summary_line_id'
    )
    total_revenue = fields.Monetary(string='Tổng doanh thu', compute='_compute_total_revenue', store=True)

    # Kế hoạch (tấn) - Dựa trên số liệu mục 2
    planned_quantity = fields.Float(string='Kế hoạch', digits="Product Unit of Measure")
    
    # Doanh thu tiền về - Chi tiết thanh toán
    total_payment_received = fields.Monetary(string='Doanh thu tiền về', compute='_compute_total_payment_received', store=True)
    
    # Xuất hóa đơn trước - Chi tiết hóa đơn
    total_invoice_quantity = fields.Float(string='Số lượng xuất HĐ trước', compute='_compute_total_invoice_amount', store=True)
    total_invoice_amount = fields.Monetary(string='Xuất HĐ trước', compute='_compute_total_invoice_amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('detail_line_ids.total_amount', 'detail_line_ids.line_type')
    def _compute_total_revenue(self):
        for record in self:
            revenue_lines = record.detail_line_ids.filtered(lambda line: line.line_type == 'revenue')
            record.total_revenue = sum(revenue_lines.mapped('total_amount'))
            record.production_quantity = sum(revenue_lines.filtered(lambda l:l.unit_price > 0).mapped('quantity'))
    
    @api.depends('detail_line_ids.total_amount', 'detail_line_ids.line_type', 'detail_line_ids.payment_id')
    def _compute_total_payment_received(self):
        for record in self:
            payment_lines = record.detail_line_ids.filtered(lambda line: line.line_type == 'payment')
            record.total_payment_received = sum(payment_lines.filtered(lambda l:l.payment_id).mapped('amount'))
    
    @api.depends('detail_line_ids.total_amount', 'detail_line_ids.line_type')
    def _compute_total_invoice_amount(self):
        for record in self:
            invoice_lines = record.detail_line_ids.filtered(lambda line: line.line_type == 'invoice')
            record.total_invoice_amount = sum(invoice_lines.mapped('total_amount'))
            record.total_invoice_quantity = sum(invoice_lines.mapped('quantity'))
    
    def _prepare_revenue_line_from_stock_move(self, summary_line_id, stock_moves, date_from, date_to):
        """Tạo line doanh thu từ stock.move"""
        self.ensure_one()
        vals = []
        for stock_move in stock_moves:
            sign = 1
            if stock_move.location_id.usage == 'customer':
                sign = -1
            sale_line = stock_move.sale_line_id
            sale_order = sale_line.order_id
            quantity = stock_move.quantity_done * sign
            price_unit = sale_line.price_unit
            product_id = stock_move.product_id.id
            taxes = sale_line.tax_id.sudo().compute_all(price_unit, sale_line.currency_id, quantity, product=sale_line.product_id)
            price_subtotal = taxes['total_excluded']
            price_subtotal_tax = taxes['total_included']
            amount_tax = price_subtotal_tax - price_subtotal
            move_ids = sale_line.invoice_lines.move_id.filtered(lambda move: move.state == 'posted' and move.date >= date_from.date() and move.date <= date_to.date())
            # Đơn hàng (nếu có), diễn giải giao dịch, số tiền, ngày, hóa đơn đã đối soát 
            
            vals.append({
                'line_type': 'revenue',
                'invoice_ids': [(6, 0, move_ids.ids)],
                'summary_line_id': summary_line_id,
                'sale_order_ids': [(6, 0, sale_order.ids)],
                'partner_id': sale_order.partner_id.id,
                'product_id': product_id,
                'delivery_date': stock_move.date.date(),
                'quantity': quantity,
                'unit_price': price_unit,
                'amount_untaxed': price_subtotal,
                'amount_total': price_subtotal_tax,
                'amount_tax': amount_tax,
            })
        
        return vals

    def _prepare_discount_line_from_sale_orders(self, summary_line_id, stock_moves, date_from, date_to):
        """Tạo line chiết khấu thương mại từ SO lines có price_unit < 0 mà không có stock.move.

        Khi một SO có dòng chiết khấu thương mại (ví dụ: [CK.KM26.KX]),
        dòng này không tạo stock.move (qty_delivered=0) nên bị bỏ sót
        khi chỉ tính doanh thu từ stock.move. Method này bổ sung các
        dòng chiết khấu đó vào chi tiết doanh thu.
        """
        self.ensure_one()
        vals = []
        # Lấy tất cả SO đã có stock.move giao hàng
        sale_orders = stock_moves.mapped('sale_line_id.order_id')
        processed_lines = set()  # Tránh trùng lặp

        for so in sale_orders:
            # Tìm SO lines chiết khấu: price < 0,
            # và không có stock.move (qty_delivered == 0)
            discount_lines = so.order_line.filtered(
                lambda l: l.price_unit < 0
                and l.qty_delivered == 0
            )
            for dl in discount_lines:
                if dl.id in processed_lines:
                    continue
                processed_lines.add(dl.id)

                # Lấy ngày giao hàng đại diện từ stock.move cùng SO
                so_moves = stock_moves.filtered(
                    lambda sm: sm.sale_line_id.order_id == so
                )
                representative_date = so_moves[:1].date.date() if so_moves else date_from.date()

                # Lấy hoá đơn liên quan trong tháng
                move_ids = dl.invoice_lines.move_id.filtered(
                    lambda move: move.state == 'posted'
                    and move.date >= date_from.date()
                    and move.date <= date_to.date()
                )

                quantity = dl.product_uom_qty
                price_unit = dl.price_unit
                taxes = dl.tax_id.sudo().compute_all(
                    price_unit, dl.currency_id, quantity, product=dl.product_id
                )
                price_subtotal = taxes['total_excluded']
                price_subtotal_tax = taxes['total_included']
                amount_tax = price_subtotal_tax - price_subtotal

                vals.append({
                    'line_type': 'revenue',
                    'invoice_ids': [(6, 0, move_ids.ids)],
                    'summary_line_id': summary_line_id,
                    'sale_order_ids': [(6, 0, [so.id])],
                    'partner_id': so.partner_id.id,
                    'product_id': dl.product_id.id,
                    'delivery_date': representative_date,
                    'quantity': quantity,
                    'unit_price': price_unit,
                    'amount_untaxed': price_subtotal,
                    'amount_total': price_subtotal_tax,
                    'amount_tax': amount_tax,
                })

        return vals

    def _prepare_payment_line_from_aml(self, amls):
        """Tạo line payment từ account.payment"""
        self.ensure_one()
        
        vals = []
        for aml in amls:
            payment = aml.payment_id
            amount = abs(aml.balance)
            payment_date = aml.date
            communication =  aml.name or ''
            partner_id = aml.partner_id.id
            order_ids = False
            if payment:
                order_ids = payment.mapped('reconciled_invoice_ids.invoice_line_ids.sale_line_ids.order_id')
                if not order_ids:
                    order_ids = payment.mapped('sale_id')
                    order_ids |= payment.mapped('sale_ids')
            
            vals.append({
                'line_type': 'payment',
                'summary_line_id': self.summary_id.id,
                'sale_order_ids': [(6, 0, order_ids.ids)] if order_ids else False,
                'partner_id': partner_id,
                'payment_id': payment.id,
                'payment_date': payment_date,
                'communication': communication,
                'amount': amount,
                'amount_total': amount,
                'amount_untaxed': amount,
            })
        
        return vals

    def _prepare_invoice_line_from_invoice(self, summary_line_id, stock_move, invoices):
        """Tạo line invoice từ account.move - tạo một dòng cho mỗi product"""
        self.ensure_one()
        
        # Lấy thông tin chung từ invoice
        sale_line = stock_move.sale_line_id
        quantity = stock_move.quantity_done
        price_unit = sale_line.price_unit
        product_id = stock_move.product_id
        taxes = sale_line.tax_id.sudo().compute_all(price_unit, sale_line.currency_id, quantity, product=product_id)
        price_subtotal = taxes['total_excluded']
        price_subtotal_tax = taxes['total_included']
        amount_tax = price_subtotal_tax - price_subtotal

        vals = {
            'line_type': 'invoice',
            'summary_line_id': summary_line_id,
            'invoice_ids': [(6, 0, invoices.ids)],
            'sale_order_ids': [(6, 0, sale_line.order_id.ids)],
            'partner_id': stock_move.partner_id.id,
            'invoice_date': max(invoices.mapped('date')),
            'product_id': product_id.id,
            'amount_untaxed': price_subtotal,
            'amount_total': price_subtotal_tax,
            'amount_tax': amount_tax,
            'quantity': quantity,
            'unit_price': price_unit,
        }
        
        return [vals]

    def action_view_detail_lines(self):
        """Action để mở view chi tiết các dòng"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết dòng tổng hợp',
            'res_model': 'salary.sales.summary.detail.line',
            'view_mode': 'tree',
            'domain': [('summary_line_id', '=', self.id)],
            'context': {
                'default_summary_line_id': self.id,
                'default_summary_id': self.summary_id.id,
                'search_default_group_team': 1,
            },
            'target': 'current',
        }
    
    def action_view_revenue_lines(self):
        """Action để mở view chi tiết doanh thu"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết doanh thu',
            'res_model': 'salary.sales.summary.detail.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('biz_kpi_business_salary.view_salary_sales_summary_detail_line_revenue_tree').id, 'tree')],
            'domain': [('summary_line_id', '=', self.id), ('line_type', '=', 'revenue')],
            'context': {
                'default_summary_line_id': self.id,
                'default_summary_id': self.summary_id.id,
                'default_line_type': 'revenue',
            },
            'target': 'current',
        }
    
    def action_view_payment_lines(self):
        """Action để mở view chi tiết doanh thu tiền về"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết doanh thu tiền về',
            'res_model': 'salary.sales.summary.detail.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('biz_kpi_business_salary.view_salary_sales_summary_detail_line_payment_tree').id, 'tree')],
            'domain': [('summary_line_id', '=', self.id), ('line_type', '=', 'payment')],
            'context': {
                'default_summary_line_id': self.id,
                'default_summary_id': self.summary_id.id,
                'default_line_type': 'payment',
            },
            'target': 'current',
        }
    
    def action_view_invoice_lines(self):
        """Action để mở view chi tiết xuất hóa đơn trước"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết xuất hóa đơn trước',
            'res_model': 'salary.sales.summary.detail.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('biz_kpi_business_salary.view_salary_sales_summary_detail_line_invoice_tree').id, 'tree')],
            'domain': [('summary_line_id', '=', self.id), ('line_type', '=', 'invoice')],
            'context': {
                'default_summary_line_id': self.id,
                'default_summary_id': self.summary_id.id,
                'default_line_type': 'invoice',
            },
            'target': 'current',
        }
