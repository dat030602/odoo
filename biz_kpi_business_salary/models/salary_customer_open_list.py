from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SalaryCustomerOpenList(models.Model):
    """Danh sách khách hàng mở"""
    _name = 'salary.customer.open.list'
    _description = 'Salary Customer Open List'
    _order = 'partner_id'

    name = fields.Char(string='Tên', related='partner_id.name')
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Khách hàng', required=True)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    
    # Thông tin khách hàng
    quantity = fields.Float(string='Số lượng', digits="Product Unit of Measure", compute='_compute_customer_data', store=True)
    unit_price = fields.Monetary(
        string='Đơn giá', 
        compute='_compute_unit_price', 
        store=True, 
        readonly=False,
        groups='hr_payroll.group_hr_payroll_user,biz_ccv_account.group_sales_team_leader'
    )
    achievement_rate = fields.Float(string='Tỷ lệ (%)', compute='_compute_customer_data', store=True)
    commission_amount = fields.Monetary(
        string='Hoa hồng', 
        compute='_compute_commission_amount', 
        store=True,
        groups='hr_payroll.group_hr_payroll_user,biz_ccv_account.group_sales_team_leader'
    )
    user_id = fields.Many2one('res.users', string='Nhân viên phụ trách', compute='_compute_customer_data', store=True)
    team_id = fields.Many2one('crm.team', string='Đội ngũ kinh doanh', related="partner_id.team_id")
    team_name = fields.Char(string='Khu vực', related='team_id.report_name', store=True)
    
    # Điều kiện áp dụng
    first_order_date = fields.Date(string='Ngày đặt hàng đầu tiên', compute='_compute_customer_data', store=True)
    
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('summary_id.month', 'summary_id.year', 'achievement_rate')
    def _compute_unit_price(self):
        for rec in self:
            try:
                month_int = int(rec.summary_id.month)
                year_int = int(rec.summary_id.year)
            except Exception:
                month_int = 0
                year_int = 0

            # Từ tháng 5/2026 trở đi tự động tính đơn giá theo tỷ lệ
            if year_int > 2026 or (year_int == 2026 and month_int >= 5):
                team_name = rec.team_name
                # Chỉ tính đơn giá cho 5 khu vực nằm trong kế hoạch
                if team_name in ['Khu vực 1', 'Khu vực 2', 'Khu vực 3', 'Khu vực 4', 'Khu vực 5']:
                    rate = rec.achievement_rate
                    if rate < 0.7:
                        rec.unit_price = 0.0
                    elif 0.7 <= rate < 0.8:
                        rec.unit_price = 15000.0
                    elif 0.8 <= rate < 0.9:
                        rec.unit_price = 20000.0
                    elif 0.9 <= rate <= 1.0:
                        rec.unit_price = 28000.0
                    else:  # rate > 1.0
                        rec.unit_price = 40000.0
                else:
                    rec.unit_price = 0.0
            else:
                # Trước tháng 5/2026, bảo toàn giá trị cũ hoặc đặt 100,000đ
                rec.unit_price = rec.unit_price or 100000.0

    @api.depends('quantity', 'unit_price', 'achievement_rate', 'summary_id.month', 'summary_id.year')
    def _compute_commission_amount(self):
        for rec in self:
            try:
                month_int = int(rec.summary_id.month)
                year_int = int(rec.summary_id.year)
            except Exception:
                month_int = 0
                year_int = 0

            commission_amount = 0
            if year_int > 2026 or (year_int == 2026 and month_int >= 5):
                # Từ tháng 5/2026: Hoa hồng = Số lượng * Đơn giá
                commission_amount = rec.quantity * rec.unit_price
            else:
                # Trước tháng 5/2026: Đạt >= 90% mới có hoa hồng
                if rec.achievement_rate >= 0.9:
                    commission_amount = rec.quantity * rec.unit_price
            rec.commission_amount = commission_amount

    @api.depends(
        'summary_id.month',
        'summary_id.year',
        'partner_id',
        'summary_id.total_line_ids.achievement_rate',
        'summary_id.line_ids.detail_line_ids.line_type',
        'summary_id.line_ids.detail_line_ids.partner_id',
        'summary_id.line_ids.detail_line_ids.quantity',
        'summary_id.line_ids.detail_line_ids.unit_price',
        'summary_id.line_ids.detail_line_ids.sale_order_ids',
        'summary_id.line_ids.detail_line_ids.sale_order_ids.order_line.product_id',
        'summary_id.line_ids.detail_line_ids.sale_order_ids.order_line.is_promotional_product',
    )
    def _compute_customer_data(self):
        for record in self:
            record.first_order_date = False
            record.user_id = False
            record.achievement_rate = 0.0
            record.quantity = 0.0
            
            # Kiểm tra nếu summary_id không tồn tại (đang trong quá trình xóa)
            if not record.summary_id or not record.summary_id.exists():
                continue
                
            if not record.summary_id.month or not record.summary_id.year or not record.partner_id:
                continue

            try:
                revenue_lines = record.summary_id.line_ids.detail_line_ids.filtered(
                    lambda line: line.line_type == 'revenue'
                )
                commissionable_lines = revenue_lines.filtered(record._is_commissionable_revenue_line)
                lines = commissionable_lines.filtered(
                    lambda line: line.partner_id == record.partner_id
                )
                # Lấy user_id từ sale.order thay vì partner_id
                sale_order_ids = lines.mapped('sale_order_ids')
                user_ids = sale_order_ids.mapped('user_id')
                record.user_id = user_ids[0] if user_ids else False

                # Tìm đơn hàng đầu tiên của khách hàng
                first_order = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('state', 'in', ['sale', 'done'])
                ], order='date_order asc', limit=1)
                
                if first_order:
                    record.first_order_date = first_order.date_order.date()
                    
                # Tính tỷ lệ sản lượng đề ra (achievement_rate)
                try:
                    month_int = int(record.summary_id.month)
                    year_int = int(record.summary_id.year)
                except Exception:
                    month_int = 0
                    year_int = 0

                if year_int > 2026 or (year_int == 2026 and month_int >= 5):
                    # Từ tháng 5/2026: Tính theo sản lượng mở mới thực tế / kế hoạch mở mới
                    team = record.partner_id.team_id
                    team_name = team.report_name if team else False
                    if team and team_name:
                        plans = {
                            'Khu vực 1': 192.7,
                            'Khu vực 2': 102.0,
                            'Khu vực 3': 108.0,
                            'Khu vực 4': 149.0,
                            'Khu vực 5': 156.8,
                        }
                        if team_name in plans:
                            plan_qty = plans[team_name]
                            all_lines = commissionable_lines
                            try:
                                open_lines = all_lines.filtered(
                                    lambda l: any(so.x_studio_n_hng_u_tin_ca_khch_hng == 'Yes' for so in l.sale_order_ids)
                                )
                            except Exception:
                                open_lines = all_lines
                            open_partners = open_lines.mapped('partner_id')
                            team_open_partners = open_partners.filtered(lambda p: p.team_id == team)
                            team_revenue_lines = all_lines.filtered(lambda l: l.partner_id in team_open_partners)
                            total_open_qty = sum(team_revenue_lines.mapped('quantity'))
                            record.achievement_rate = (total_open_qty / plan_qty) if plan_qty > 0 else 0.0
                        else:
                            record.achievement_rate = 0.0
                    else:
                        record.achievement_rate = 0.0
                else:
                    # Trước tháng 5/2026: Dùng công thức cũ
                    if record.partner_id.team_id:
                        record.achievement_rate = record.summary_id.total_line_ids.filtered(lambda line: line.team_id == record.partner_id.team_id).achievement_rate or 0
                    else:
                        record.achievement_rate = 0.0
                
                record.quantity = sum(lines.mapped('quantity'))
                
            except Exception as e:
                _logger.warning(f"Lỗi khi tính toán dữ liệu khách hàng cho record {record.id}: {str(e)}")
                record.achievement_rate = 0.0
                record.quantity = 0.0

    def action_view_customer_orders(self):
        """Action để xem đơn hàng của khách hàng"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Đơn hàng của {self.partner_id.name}',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {
                'default_partner_id': self.partner_id.id,
            },
            'target': 'current',
        }

    def action_view_customer_summary_lines(self):
        """Action để xem summary lines của khách hàng"""
        self.ensure_one()
        
        summary_lines = self.summary_id.line_ids.filtered(
            lambda line: self.partner_id in line.detail_line_ids.mapped('partner_id')
        )
        
        if summary_lines:
            return {
                'type': 'ir.actions.act_window',
                'name': f'Chi tiết tổng hợp - {self.partner_id.name}',
                'res_model': 'salary.sales.summary.line',
                'res_ids': summary_lines.ids,
                'view_mode': 'tree,form',
                'domain': [('id', 'in', summary_lines.ids)],
                'context': {
                    'default_summary_id': self.summary_id.id,
                    'default_partner_id': self.partner_id.id,
                },
                'target': 'current',
            }
        return False

    @api.model
    def _is_commissionable_revenue_line(self, line):
        if line.line_type != 'revenue' or line.unit_price <= 0:
            return False

        sale_lines = line.sale_order_ids.order_line.filtered(
            lambda sale_line: sale_line.product_id == line.product_id
        )
        return not any(getattr(sale_line, 'is_promotional_product', False) for sale_line in sale_lines)

    @api.model
    def create_from_summary_data(self, summary_id):
        """Tạo dữ liệu từ summary data"""
        if not summary_id:
            return False
        
        summary = self.env['salary.sales.summary'].browse(summary_id)
        if not summary:
            return False
        
        # Xóa dữ liệu cũ
        self.search([('summary_id', '=', summary_id)]).unlink()
        
        # Lấy danh sách khách hàng từ summary lines thông qua detail lines
        lines = summary.line_ids.detail_line_ids.filtered(self._is_commissionable_revenue_line)
        
        # Lọc theo custom field nếu có (sử dụng try-except để tránh lỗi nếu field không tồn tại)
        try:
            lines = lines.filtered(
                lambda line: any(so.x_studio_n_hng_u_tin_ca_khch_hng == 'Yes' for so in line.sale_order_ids)
            )
        except Exception:
            # Nếu custom field không tồn tại, sử dụng tất cả lines
            pass
        partners = lines.mapped('partner_id')
        
        # Tạo dữ liệu cho từng khách hàng
        vals_list = []
        for partner in partners:
            vals_list.append({
                'summary_id': summary_id,
                'partner_id': partner.id,
            })
        
        return self.create(vals_list)

    def unlink(self):
        """Override unlink để xử lý việc xóa an toàn"""
        try:
            return super().unlink()
        except Exception as e:
            for record in self:
                try:
                    record.unlink()
                except Exception as record_error:
                    pass
            raise

    @api.model
    def cleanup_orphaned_records(self):
        """Dọn dẹp các record bị orphaned (không có summary_id hoặc partner_id hợp lệ)"""
        # Tìm các record có summary_id không tồn tại
        orphaned_summary = self.search([
            ('summary_id', '!=', False)
        ]).filtered(lambda r: not r.summary_id.exists())
        
        # Tìm các record có partner_id không tồn tại
        orphaned_partner = self.search([
            ('partner_id', '!=', False)
        ]).filtered(lambda r: not r.partner_id.exists())
        
        # Tìm các record có summary_id = False
        null_summary = self.search([('summary_id', '=', False)])
        
        # Tìm các record có partner_id = False
        null_partner = self.search([('partner_id', '=', False)])
        
        # Gộp tất cả các record cần xóa
        records_to_delete = orphaned_summary | orphaned_partner | null_summary | null_partner
        
        if records_to_delete:
            try:
                records_to_delete.unlink()
            except Exception as e:
                pass
        
        return len(records_to_delete)
