from odoo import models, fields, api
import unicodedata
import logging

_logger = logging.getLogger(__name__)

class SalaryHumicSalesDetail(models.Model):
    """Sổ chi tiết bán hàng sản phẩm humic"""
    _name = 'salary.humic.sales.detail'
    _description = 'Salary Humic Sales Detail'
    _order = 'team_id, partner_id, product_id'

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    
    # Thông tin hóa đơn
    invoice_ids = fields.Many2many(
        'account.move',
        'account_move_salary_humic_sales_detail_rel',
        'humic_sales_detail_id',
        'account_move_id',
        string='Hóa đơn'
    )
    invoice_name = fields.Char(string='Số hóa đơn', compute='_compute_invoice_name', store=True)
    
    # Thông tin khách hàng và sản phẩm
    partner_id = fields.Many2one('res.partner', string='Khách hàng', readonly=True)
    user_id = fields.Many2one('res.users', string='Nhân viên phụ trách', compute='_compute_user_id', store=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='ĐVT', related='product_id.uom_id', store=True)
    
    # Thông tin số lượng và giá
    quantity = fields.Float(string='Số lượng', digits="Product Unit of Measure", required=True)
    unit_price = fields.Monetary(string='Đơn giá', required=True)
    total_amount = fields.Monetary(string='Doanh số sau thuế', compute='_compute_amounts', store=True)
    amount_paid = fields.Monetary(string='Tiền thu', compute='_compute_amount_paid', store=True)
    
    # Hoa hồng
    commission_unit_price = fields.Monetary(
        string='Đơn giá Hoa hồng', 
        required=True,
        groups='hr_payroll.group_hr_payroll_user,biz_ccv_account.group_sales_team_leader'
    )
    commission_amount = fields.Monetary(
        string='Tiền hoa hồng', 
        compute='_compute_amounts', 
        store=True,
        groups='hr_payroll.group_hr_payroll_user,biz_ccv_account.group_sales_team_leader'
    )
    employee_commission_amount = fields.Monetary(
        string='Hoa hồng nhân viên',
        compute='_compute_amounts',
        store=True,
        groups='hr_payroll.group_hr_payroll_user,biz_ccv_account.group_sales_team_leader'
    )
    
    # Khu vực
    team_id = fields.Many2one('crm.team', string='Đội ngũ kinh doanh', readonly=True)
    team_name = fields.Char(string='Khu vực', readonly=True)

    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('invoice_ids.amount_residual', 'total_amount')
    def _compute_amount_paid(self):
        for record in self:
            if not record.invoice_ids:
                amount_paid = 0.0
            else:
                amount_paid = sum(record.invoice_ids.filtered(lambda inv: inv.amount_total > 0).mapped('amount_residual')) - record.total_amount
            record.amount_paid = record.total_amount if amount_paid < 0 else 0.0

    @api.depends('invoice_ids.vat_sinvoice_number')
    def _compute_invoice_name(self):
        for record in self:
            record.invoice_name = ', '.join(str(vat_inv) for vat_inv in record.invoice_ids.mapped('vat_sinvoice_number') if vat_inv)

    @api.depends('invoice_ids.invoice_line_ids.sale_line_ids.order_id.user_id')
    def _compute_user_id(self):
        for record in self:
            sale_orders = record.invoice_ids.invoice_line_ids.sale_line_ids.order_id
            users = sale_orders.mapped('user_id')
            record.user_id = users[:1].id if users else False
    
    @api.depends('quantity', 'unit_price', 'commission_unit_price')
    def _compute_amounts(self):
        for record in self:
            record.total_amount = record.quantity * record.unit_price
            record.commission_amount = record.commission_unit_price * record.quantity
            record.employee_commission_amount = record.commission_amount * 0.45

    @api.depends('invoice_name', 'partner_id.name', 'product_id.name')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.invoice_name or ''} - {record.partner_id.name or ''} - {record.product_id.name or ''}"

    @api.model
    def create_from_summary_detail_lines(self, summary_id):
        """Tạo dữ liệu từ summary detail lines"""
        self = self.with_context(lang='vi_VN')
        if not summary_id:
            return False
        
        summary = self.env['salary.sales.summary'].browse(summary_id)
        if not summary:
            return False
        
        # Xóa dữ liệu cũ
        self.search([('summary_id', '=', summary_id)]).unlink()
        
        # Lấy tất cả detail lines từ summary
        all_detail_lines = summary.line_ids.detail_line_ids.filtered(lambda line: line.line_type == 'revenue')
        
        # Lọc detail lines có sản phẩm humic
        humic_keywords = ['humic', 'humate']
        # humic_keywords += ['10-60-10', '20-20-20', '52-34']
        humic_not_keywords = ['lân đen']
        humic_detail_lines = all_detail_lines.filtered(lambda line: any([kw in (line.product_id.name or '').lower() for kw in humic_keywords])) \
            - all_detail_lines.filtered(lambda line: any([kw in (line.product_id.name or '').lower() for kw in humic_not_keywords]))
        
        if not humic_detail_lines:
            return False

        # Tạo dữ liệu mới
        vals_list = []
        for detail_line in humic_detail_lines.filtered(lambda line: line.quantity > 0):
            # Lấy đơn giá hoa hồng từ danh mục đơn vị tính
            commission_price = self._get_commission_price(detail_line.product_id, detail_line.product_id.default_specification_id)
            
            vals_list.append({
                'summary_id': summary_id,
                'invoice_ids': [(6, 0, detail_line.invoice_ids.ids)],
                'partner_id': detail_line.partner_id.id,
                'user_id': detail_line.sale_order_ids[:1].user_id.id if detail_line.sale_order_ids else False,
                'team_id': detail_line.team_id.id,
                'team_name': detail_line.name,
                'product_id': detail_line.product_id.id,
                'quantity': detail_line.quantity,
                'unit_price': detail_line.unit_price,
                'commission_unit_price': commission_price,
            })
        return self.create(vals_list)

    def _get_commission_price(self, product, uom):
        """Lấy đơn giá hoa hồng từ đơn vị tính"""
        if not self._is_one_kg_bag(product, uom):
            return 80000.0
        if uom and uom.commission_price:
            return uom.commission_price
        else:
            return 0.0

    def _is_one_kg_bag(self, product, uom):
        def normalize(value):
            value = unicodedata.normalize('NFKD', value or '')
            value = ''.join(ch for ch in value if not unicodedata.combining(ch))
            return value.lower()

        text = ' '.join([
            normalize(product.name),
            normalize(product.default_code),
            normalize(uom.name if uom else ''),
        ])
        compact_text = text.replace(' ', '')
        has_one_kg = '1kg' in compact_text or '1000g' in compact_text
        has_bag = any(keyword in text for keyword in ['tui', 'goi', 'bao', 'bag'])
        return has_one_kg and has_bag

    def action_view_invoice(self):
        """Action để xem chi tiết hóa đơn"""
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(self.invoice_ids) > 1:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        elif len(self.invoice_ids) == 1:
            action['res_id'] = self.invoice_ids.id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
        return action

    def action_view_sale_order(self):
        """Action để xem chi tiết đơn hàng"""
        self.ensure_one()
        
        sale_order = self.invoice_ids.invoice_line_ids.sale_line_ids.order_id
        action = self.env.ref('sale.action_orders').sudo().read()[0]
        if len(sale_order) != 1:
            action['domain'] = [('id', 'in', sale_order.ids)]
        elif len(sale_order) == 1:
            action['res_id'] = sale_order.id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
        return action


