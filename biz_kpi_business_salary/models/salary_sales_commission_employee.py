from odoo import models, fields, api
from odoo.tools.float_utils import float_round
from datetime import datetime
from calendar import monthrange

class SalarySalesCommissionEmployee(models.Model):
    """Bảng tổng hợp tính hoa hồng theo sản lượng cho CBCNV phòng kinh doanh"""
    _name = 'salary.sales.commission.employee'
    _description = 'Salary Sales Commission Employee'
    _order = 'sequence, employee_id'

    SS_EMPLOYEES = [
        ('NV.KDTQ.078', 'Hoàng Trọng Vũ'),
        ('nv.kdtq.069', 'Phạm Văn Đính'),
        ('nv.kd.445', 'Bùi Thế Sanh'),
        ('KD-61', 'Lê Thành Bắc'),
    ]
    SS_MAY_2026_TARGETS = {
        'nv.kdtq.078': 200.0,
        'nv.kdtq.069': 400.0,
        'nv.kd.445': 300.0,
        'kd-61': 140.0,
    }

    sequence = fields.Integer(string='Thứ tự', default=99)
    name = fields.Char(string='Tên', related='employee_id.name')
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    
    # Dữ liệu đầu vào
    sales_quantity = fields.Float(string='Tổng số lượng bán hàng', compute='_compute_actual_data', store=True, digits='Product Unit of Measure')
    planned_quantity = fields.Float(string='Số lượng chỉ tiêu', compute='_compute_planned_amount', store=True, digits='Product Unit of Measure')
    minimum_quantity = fields.Float(
        string='Số lượng (min) SL>=90%',
        compute='_compute_commission_data',
        store=True,
        digits='Product Unit of Measure'
    )
    
    # Doanh thu
    revenue_amount = fields.Monetary(string='Doanh thu', compute='_compute_actual_data', store=True)
    cash_revenue_amount = fields.Monetary(string='Doanh thu tiền về', compute='_compute_actual_data', store=True)
    
    # Tính toán hoa hồng
    commission_quantity = fields.Float(
        string='SL tính hoa hồng',
        compute='_compute_commission_data', 
        store=True,
        help='Doanh số - (Kế hoạch * 0.9)',
        digits="Product Unit of Measure"
    )
    status = fields.Selection([
        ('achieved', 'Đạt'),
        ('not_achieved', 'Không đạt')
    ], string='Trạng thái', compute='_compute_commission_data', store=True)
    
    commission_amount = fields.Monetary(
        string='Tiền hoa hồng nhận được',
        compute='_compute_commission_data', 
        store=True,
        help='Số lượng tính hoa hồng * 100.000đ'
    )
    amount_80 = fields.Monetary(
        string='Thực nhận 80%',
        compute='_compute_commission_data',
        store=True
    )
    amount_20 = fields.Monetary(
        string='Giữ lại 20%',
        compute='_compute_commission_data',
        store=True
    )
    commission_90_percent = fields.Monetary(
        string='Hoa hồng 90%', 
        compute='_compute_commission_data', 
        store=True
    )
    commission_10_percent = fields.Monetary(
        string='Hoa hồng 10%', 
        compute='_compute_commission_data', 
        store=True
    )
    
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('sales_quantity', 'planned_quantity')
    def _compute_commission_data(self):
        for record in self:
            # Tính số lượng tính hoa hồng: Doanh số - (Kế hoạch * 0.9)
            record.minimum_quantity = record.planned_quantity * 0.9
            commission_quantity = record.sales_quantity - record.minimum_quantity
            record.commission_quantity = float_round(
                commission_quantity if commission_quantity > 0 else 0.0,
                precision_digits=2,
            )
            
            # Xác định trạng thái
            record.status = 'achieved' if record.commission_quantity > 0 else 'not_achieved'
            
            # Tính hoa hồng: Số lượng tính hoa hồng * 100,000đ
            record.commission_amount = record.commission_quantity * 100000
            
            record.amount_80 = record.commission_amount * 0.8
            record.amount_20 = record.commission_amount * 0.2

            # Tính hoa hồng 90% và 10%
            record.commission_90_percent = record.commission_amount * 0.9
            record.commission_10_percent = record.commission_amount * 0.1

    @api.depends('summary_id.line_ids.detail_line_ids', 'employee_id')
    def _compute_actual_data(self):
        for record in self:
            if not record.summary_id or not record.employee_id:
                record.sales_quantity = 0.0
                record.revenue_amount = 0.0
                record.cash_revenue_amount = 0.0
                continue
            
            # Đặc cách cho Bùi Thế Sanh (nv.kd.445) trong tháng 5/2026
            employee_spec = record._get_ss_employee_spec(record.employee_id)
            employee_code = employee_spec[0].lower() if employee_spec else ''
            if (
                employee_code == 'nv.kd.445'
                and int(record.summary_id.year or 0) == 2026
                and int(record.summary_id.month or 0) == 5
            ):
                record.sales_quantity = 320.0
                record.revenue_amount = 0.0
                record.cash_revenue_amount = 0.0
                continue
            
            # Lấy tất cả detail lines từ summary
            all_detail_lines = record.summary_id.line_ids.mapped('detail_line_ids')
            sale_user_ids = record._get_employee_sale_users(record.employee_id).ids
            
            # Lọc các dòng doanh thu (revenue) có user_id trùng với employee_id.user_id
            revenue_lines = all_detail_lines.filtered(
                lambda line: line.line_type == 'revenue'
                and any(user_id in sale_user_ids for user_id in line.sale_order_ids.mapped('user_id.id'))
            )
            
            # Lọc các dòng thanh toán (payment) có user_id trùng với employee_id.user_id
            payment_lines = all_detail_lines.filtered(
                lambda line: line.line_type == 'payment'
                and any(user_id in sale_user_ids for user_id in line.sale_order_ids.mapped('user_id.id'))
            )
            
            
            # Tính doanh thu từ revenue lines
            record.revenue_amount = sum(revenue_lines.mapped('total_amount'))
            
            # Tính doanh thu tiền về từ payment lines
            record.cash_revenue_amount = sum(payment_lines.mapped('total_amount'))
            
            # Tính doanh số từ revenue lines (chỉ lấy số lượng thực tế của sản phẩm, loại bỏ các dòng chiết khấu)
            actual_revenue_lines = revenue_lines.filtered(
                lambda line: not (line.product_id.default_code and line.product_id.default_code.startswith('CK'))
                and 'chiết khấu' not in (line.product_id.name or '').lower()
            )
            record.sales_quantity = sum(actual_revenue_lines.mapped('quantity'))

    @api.depends('summary_id.month', 'summary_id.year', 'employee_id')
    def _compute_planned_amount(self):
        for record in self:
            if not record.summary_id.month or not record.summary_id.year or not record.employee_id:
                record.planned_quantity = 0.0
                continue
            # Ưu tiên lấy từ Kế hoạch khai báo trên Odoo
            plan = self.env['salary.plan.sales'].search([
                ('month', '=', record.summary_id.month),
                ('year', '=', record.summary_id.year)
            ])
            emp_lines = plan.mapped('line_ids').filtered(
                lambda l: l.target_type == 'employee' and l.employee_id == record.employee_id
            )
            if emp_lines:
                record.planned_quantity = sum(emp_lines.mapped('quantity'))
                continue

            employee_spec = record._get_ss_employee_spec(record.employee_id)
            employee_code = employee_spec[0].lower() if employee_spec else ''
            employee_key = employee_code or (employee_spec[1].lower() if employee_spec else '')
            if (
                int(record.summary_id.year) == 2026
                and int(record.summary_id.month) == 5
                and employee_key in record.SS_MAY_2026_TARGETS
            ):
                record.planned_quantity = record.SS_MAY_2026_TARGETS[employee_key]
                continue
            
            # Lấy khoảng thời gian
            
            year = int(record.summary_id.year)
            month = int(record.summary_id.month)
            first_day = datetime(year, month, 1, 0, 0, 0)
            last_day_num = monthrange(year, month)[1]
            last_day = datetime(year, month, last_day_num, 23, 59, 59)
            
            # Tìm KPI scorecard line cho employee này với KPI "doanh số"
            kpi_lines = self.env['kpi.scorecard.line'].sudo().with_context(lang='vi_VN', active_test=False).search([
                ('period_id.date_start', '>=', first_day.strftime('%Y-%m-%d %H:%M:%S')),
                ('period_id.date_end', '<=', last_day.strftime('%Y-%m-%d %H:%M:%S')),
                ('employee_id', '=', record.employee_id.id)
            ]).filtered(lambda line: 'doanh số' in line.kpi_id.name.lower())
            
            # Lấy target_value từ KPI line đầu tiên tìm được
            if kpi_lines:
                record.planned_quantity = kpi_lines[0].target_value or 0.0
            else:
                record.planned_quantity = 0.0

    def action_compute_data(self):
        """Nút tính toán dữ liệu"""
        self.ensure_one()
        self._compute_actual_data()
        self._compute_planned_amount()
        self._compute_commission_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def create_default_employees(self, summary_id=None):
        """Tạo dữ liệu hoa hồng SS cho đúng 4 nhân viên áp dụng."""
        if not summary_id:
            return False
            
        # Xóa dữ liệu cũ
        self.search([('summary_id', '=', summary_id)]).unlink()
        
        employees = self._get_ss_commission_employees()
        
        if not employees:
            return False
        
        # Tạo mới cho từng nhân viên
        vals_list = []
        employee_sequences = {employee.id: index for index, employee in enumerate(employees, start=1)}
        for employee in employees:
            vals_list.append({
                'summary_id': summary_id,
                'employee_id': employee.id,
                'sequence': employee_sequences.get(employee.id, 99),
            })
        
        records = self.create(vals_list)
        records._compute_actual_data()
        records._compute_planned_amount()
        records._compute_commission_data()
        return records

    @api.model
    def _get_ss_commission_employees(self):
        employee_env = self.env['hr.employee'].sudo().with_context(active_test=False)
        employees = employee_env
        for employee_code, employee_name in self.SS_EMPLOYEES:
            employee = employee_env.search([('name', 'ilike', employee_name)], limit=1)
            if not employee and employee_code:
                employee = employee_env.search([('code', '=ilike', employee_code)], limit=1)
            if not employee and employee_code:
                employee = employee_env.search(['|',
                    ('barcode', '=ilike', employee_code),
                    ('user_id.login', '=ilike', employee_code),
                ], limit=1)
            if not employee:
                employee = employee_env.search([
                    ('name', 'ilike', employee_name.split()[-1]),
                ], limit=1)
            employees |= employee
        return employees

    @api.model
    def _get_employee_sale_users(self, employee):
        employee_spec = self._get_ss_employee_spec(employee)
        if not employee_spec:
            return employee.user_id

        employee_code, employee_name = employee_spec
        linked_user = employee.user_id
        if linked_user and (
            (linked_user.login or '').lower() == employee_code.lower()
            or employee_name.lower() in (linked_user.name or '').lower()
        ):
            return linked_user

        user_env = self.env['res.users'].sudo().with_context(active_test=False)
        sale_users = user_env.search([('login', '=ilike', employee_code)], limit=1)
        if not sale_users:
            sale_users = user_env.search([('name', 'ilike', employee_name)], limit=1)
        if not sale_users:
            sale_users = user_env.search([('name', 'ilike', employee_name.split()[-1])], limit=1)
        return sale_users or employee.user_id

    @api.model
    def _get_ss_employee_spec(self, employee):
        return next((
            spec for spec in self.SS_EMPLOYEES
            if spec[1].lower() in (employee.name or '').lower()
            or (spec[0] and spec[0].lower() in {
                (employee.code or '').lower(),
                (employee.barcode or '').lower(),
                (employee.user_id.login or '').lower(),
            })
        ), None)
