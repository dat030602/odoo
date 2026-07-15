import unicodedata

from odoo import models, fields, api


class SalaryPersonnelCommission(models.Model):
    """Hoa hồng nhân sự khu vực theo từng nhân sự."""
    _name = 'salary.personnel.commission'
    _description = 'Salary Personnel Commission'
    _order = 'team_id, role_sequence, employee_id'

    TEAM_LEADER_PLANS = {
        'Khu vực 1': {'planned_quantity': 1734.3 + 192.7, 'progress_compensation_rate': 0.03},
        'Khu vực 2': {'planned_quantity': 922.0 + 102.0, 'progress_compensation_rate': 0.00},
        'Khu vực 3': {'planned_quantity': 976.0 + 108.0, 'progress_compensation_rate': 0.10},
        'Khu vực 4': {'planned_quantity': 1495.0 + 149.5, 'progress_compensation_rate': 0.17},
        'Khu vực 5': {'planned_quantity': 1411.2 + 156.8, 'progress_compensation_rate': 0.26},
    }
    MAY_2026_EMPLOYEE_PLANS = {
        'Khu vực 1': {
            'nguyen thi thuy trang': 577.0,
            'nguyen thai tho': 143.0,
            'vo thi diem': 200.0,
        },
        'Khu vực 2': {
            'vo thi thuy tien': 154.0,
            'do thi ngoc tu minh': 140.0,
            'nguyen thu ngan': 315.0,
        },
        'Khu vực 3': {
            'doan chi tan': 130.0,
            'nguyen thi ngoc han': 125.0,
        },
        'Khu vực 4': {
            'tran nguyen bao duyen': 591.0,
            'nguyen manh khanh': 202.0,
            'pham huynh quyen': 150.0,
            'tran thi huong': 120.0,
        },
        'Khu vực 5': {
            'le minh cua': 509.0,
            'pham van hien': 509.0,
            'ngo thi lan huyen': 300.0,
        },
    }
    MAY_2026_NO_SALES_DISCOUNT_EMPLOYEES = {
        'pham huynh quyen',
        'le minh cua',
    }

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', required=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân sự')
    employee_code = fields.Char(string='Mã nhân viên', related='employee_id.code', store=True)
    job_title = fields.Char(string='Chức danh')
    role_sequence = fields.Integer(string='Thứ tự', default=20)
    planned_quantity = fields.Float(string='Sản lượng kế hoạch', digits='Product Unit of Measure')
    actual_quantity = fields.Float(string='Sản lượng thực hiện', digits='Product Unit of Measure')
    progress_compensation_rate = fields.Float(string='Tỷ lệ bù tiến')
    allocation_rate = fields.Float(string='Tỷ trọng')

    sales_discount_80 = fields.Monetary(string='80% Chiết khấu bán hàng')
    humic_discount_80 = fields.Monetary(string='80% Chiết khấu humic')
    total_amount_80 = fields.Monetary(string='Tổng nhận 80%', compute='_compute_totals', store=True)
    sales_discount_20 = fields.Monetary(string='Giữ lại 20% bán hàng')
    humic_discount_20 = fields.Monetary(string='Giữ lại 20% humic')
    total_amount_20 = fields.Monetary(string='Tổng cộng giữ lại 20%', compute='_compute_totals', store=True)

    # Backward-compatible fields used by old reports/formulas.
    team_commission_amount = fields.Monetary(string='Tiền thưởng', compute='_compute_legacy_amounts', store=True)
    sale_support_amount = fields.Monetary(string='Sale hỗ trợ', compute='_compute_legacy_amounts', store=True)
    team_leader_amount = fields.Monetary(string='Trưởng khu vực', compute='_compute_legacy_amounts', store=True)
    department_manager_amount = fields.Monetary(string='Trưởng (Phó) phòng', compute='_compute_legacy_amounts', store=True)

    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('team_id.report_name', 'employee_id.name')
    def _compute_name(self):
        for record in self:
            record.name = '%s - %s' % (record.team_id.report_name or record.team_id.name or '', record.employee_id.name or '')

    @api.depends('sales_discount_80', 'humic_discount_80', 'sales_discount_20', 'humic_discount_20')
    def _compute_totals(self):
        for record in self:
            record.total_amount_80 = record.sales_discount_80 + record.humic_discount_80
            record.total_amount_20 = record.sales_discount_20 + record.humic_discount_20

    @api.depends('total_amount_80')
    def _compute_legacy_amounts(self):
        for record in self:
            record.team_commission_amount = record.total_amount_80
            record.sale_support_amount = 0.0
            record.team_leader_amount = record.total_amount_80 if record.job_title == 'Trưởng khu vực' else 0.0
            record.department_manager_amount = 0.0

    @api.model
    def create_from_summary_data(self, summary_id):
        if not summary_id:
            return False

        summary = self.env['salary.sales.summary'].browse(summary_id)
        if not summary.exists():
            return False

        self.search([('summary_id', '=', summary.id)]).unlink()

        team_names = ['Khu vực 1', 'Khu vực 2', 'Khu vực 3', 'Khu vực 4', 'Khu vực 5']
        teams = self.env['crm.team'].search([
            '|',
            ('report_name', 'in', team_names),
            ('name', 'in', team_names),
        ])
        if not teams:
            return False

        def team_sort_key(team):
            team_name = team.report_name if team.report_name in team_names else team.name
            return team_names.index(team_name) if team_name in team_names else len(team_names)

        teams = teams.sorted(team_sort_key)
        vals_list = []
        ss_employee_ids = self._get_ss_employee_ids()
        for team in teams:
            self._append_team_leader_line(summary, team, vals_list)
            self._append_ss_employee_lines(summary, team, vals_list, ss_employee_ids)
            self._append_sales_staff_lines(summary, team, vals_list, ss_employee_ids)

        if not vals_list:
            return False
        return self.create(vals_list)

    def _append_team_leader_line(self, summary, team, vals_list):
        employee = self.env['hr.employee'].search([
            ('user_id', '=', team.user_id.id),
        ], limit=1) if team.user_id else self.env['hr.employee']
        if not employee:
            return

        total_line = summary.total_line_ids.filtered(lambda line: line.team_id == team)[:1]
        sales_discount = summary.sales_discount_ids.filtered(
            lambda line: line.team_id == team and line.name == 'Trưởng khu vực'
        )[:1]
        if not sales_discount:
            sales_discount = summary.sales_discount_ids.filtered(
                lambda line: line.team_id == team and abs(line.rate - 0.45) < 0.0001
            )[:1]
        humic_discount = summary.humic_discount_ids.filtered(
            lambda line: line.team_id == team
            and employee in line.employee_ids
            and abs(line.rate - 0.20) < 0.0001
        )[:1]
        if not humic_discount:
            humic_discount = summary.humic_discount_ids.filtered(
                lambda line: line.team_id == team and line.name == 'Trưởng khu vực nhận từ quỹ chung'
            )[:1]
        personal_humic_amount = sum(
            summary.humic_sales_detail_ids.filtered(
                lambda line: line.team_id == team and line.user_id == employee.user_id
            ).mapped('employee_commission_amount')
        )
        team_name = team.report_name if team.report_name in self.TEAM_LEADER_PLANS else team.name
        is_may_2026 = str(summary.month) == '5' and str(summary.year) == '2026'
        
        plan = self.env['salary.plan.sales'].search([
            ('team_id', '=', team.id),
            ('month', '=', summary.month),
            ('year', '=', summary.year)
        ], limit=1)
        if plan:
            oc_lines = plan.line_ids.filtered(lambda l: l.target_type == 'oc')
            nc_lines = plan.line_ids.filtered(lambda l: l.target_type == 'nc')
            planned_quantity = sum(oc_lines.mapped('quantity')) + sum(nc_lines.mapped('quantity'))
            progress_compensation_rate = plan.progress_compensation_rate / 100.0 if plan.progress_compensation_rate else 0.0
        else:
            team_plan = self.TEAM_LEADER_PLANS.get(team_name, {}) if is_may_2026 else {}
            planned_quantity = team_plan.get('planned_quantity', 0.0)
            progress_compensation_rate = team_plan.get('progress_compensation_rate', 0.0)
            
        actual_quantity = total_line.production_quantity if total_line else 0.0
        total_rate = (
            actual_quantity / planned_quantity + progress_compensation_rate
            if planned_quantity else 0.0
        )
        achievement_rate = total_line.get_sales_discount_achievement_rate() if total_line else 0.0
        sales_discount_receive_rate = self._get_team_leader_sales_discount_receive_rate(achievement_rate)

        vals_list.append({
            'summary_id': summary.id,
            'team_id': team.id,
            'employee_id': employee.id,
            'job_title': 'Trưởng khu vực',
            'role_sequence': 10,
            'planned_quantity': planned_quantity,
            'actual_quantity': actual_quantity,
            'progress_compensation_rate': progress_compensation_rate,
            'allocation_rate': total_rate,
            'sales_discount_80': (
                (sales_discount.total_discount if sales_discount else 0.0)
                * sales_discount_receive_rate
            ),
            'humic_discount_80': (
                (humic_discount.amount_80 if humic_discount else 0.0)
                + personal_humic_amount * 0.8
            ),
            'sales_discount_20': (
                (sales_discount.total_discount if sales_discount else 0.0)
                * (1 - sales_discount_receive_rate)
            ),
            'humic_discount_20': (
                (humic_discount.amount_20 if humic_discount else 0.0)
                + personal_humic_amount * 0.2
            ),
        })

    @staticmethod
    def _get_team_leader_sales_discount_receive_rate(total_rate):
        if total_rate < 0.70:
            return 0.0
        if total_rate <= 0.80:
            return 0.80
        if total_rate < 0.90:
            return 0.90
        return 1.0

    def _append_sales_staff_lines(self, summary, team, vals_list, excluded_employee_ids=None):
        excluded_employee_ids = excluded_employee_ids or []
        revenue_lines = summary.line_ids.detail_line_ids.filtered(
            lambda line: line.line_type == 'revenue'
            and line.team_id == team
            and line.unit_price > 0
        )
        humic_lines = summary.humic_sales_detail_ids.filtered(lambda line: line.team_id == team)
        sale_users = revenue_lines.mapped('sale_order_ids.user_id') - team.user_id
        humic_users = humic_lines.mapped('user_id') - team.user_id
        employees = self.env['hr.employee'].search([
            ('user_id', 'in', (sale_users | humic_users).ids),
        ]) if sale_users or humic_users else self.env['hr.employee']
        employee_plans = self._get_employee_plans(summary, team)
        if employee_plans:
            employees |= self.env['hr.employee'].search([]).filtered(
                lambda employee: self._get_employee_plan(employee, employee_plans)[0]
            )

        employee_quantities = {}
        employee_humic_amounts = {}
        employee_planned_quantities = {}
        for employee in employees:
            if employee.id in excluded_employee_ids:
                continue
            if self._should_skip_employee_for_summary(summary, employee):
                continue
            employee_lines = revenue_lines.filtered(
                lambda line: employee.user_id.id in line.sale_order_ids.mapped('user_id.id')
            )
            quantity = sum(employee_lines.mapped('quantity'))
            humic_amount = sum(
                humic_lines.filtered(lambda line: line.user_id == employee.user_id).mapped(
                    'employee_commission_amount'
                )
            )
            has_employee_plan, planned_quantity = self._get_employee_plan(employee, employee_plans)
            if quantity or humic_amount or has_employee_plan:
                employee_quantities[employee.id] = quantity
                employee_humic_amounts[employee.id] = humic_amount
                employee_planned_quantities[employee.id] = planned_quantity

        total_quantity = sum(employee_quantities.values())
        if not employee_quantities:
            return

        sales_discount = summary.sales_discount_ids.filtered(
            lambda line: line.team_id == team and line.name == 'Khối bán hàng'
        )[:1]
        if not sales_discount:
            sales_discount = summary.sales_discount_ids.filtered(
                lambda line: line.team_id == team and abs(line.rate - 0.25) < 0.0001
            )[:1]
        total_line = summary.total_line_ids.filtered(lambda line: line.team_id == team)[:1]
        team_sales_discount_receive_rate = self._get_team_leader_sales_discount_receive_rate(
            total_line.get_sales_discount_achievement_rate() if total_line else 0.0
        )

        for employee_id, quantity in employee_quantities.items():
            employee = self.env['hr.employee'].browse(employee_id)
            sales_rate = quantity / total_quantity if total_quantity else 0.0
            humic_amount = employee_humic_amounts[employee_id]
            planned_quantity = employee_planned_quantities[employee_id]
            apply_sales_discount = (
                team_sales_discount_receive_rate > 0
                and not self._is_may_2026_no_sales_discount_employee(summary, employee)
            )
            # Custom receive rate for Tran Nguyen Bao Duyen in June 2026 (Supervisor achievement penalty)
            receive_rate = 1.0
            if (
                str(summary.month) == '6'
                and str(summary.year) == '2026'
                and 'trần nguyên bảo duyên' in (employee.name or '').lower()
            ):
                receive_rate = 0.60

            vals_list.append({
                'summary_id': summary.id,
                'team_id': team.id,
                'employee_id': employee_id,
                'job_title': 'TS',
                'role_sequence': 20,
                'planned_quantity': planned_quantity,
                'actual_quantity': quantity,
                'allocation_rate': quantity / planned_quantity if planned_quantity else 0.0,
                'sales_discount_80': (
                    (sales_discount.amount_80 if sales_discount else 0.0) * sales_rate * receive_rate
                    if apply_sales_discount else 0.0
                ),
                'humic_discount_80': humic_amount * 0.8,
                'sales_discount_20': (
                    (sales_discount.amount_20 if sales_discount else 0.0) * sales_rate * receive_rate
                    if apply_sales_discount else 0.0
                ),
                'humic_discount_20': humic_amount * 0.2,
            })

    def _get_employee_plans(self, summary, team):
        # Ưu tiên lấy từ kế hoạch khai báo trên Odoo
        plan = self.env['salary.plan.sales'].search([
            ('team_id', '=', team.id),
            ('month', '=', summary.month),
            ('year', '=', summary.year)
        ], limit=1)
        if plan:
            plans = {}
            for line in plan.line_ids.filtered(lambda l: l.target_type == 'employee'):
                if line.employee_id:
                    code = self._normalize_code(line.employee_id.code)
                    if code:
                        plans[code] = line.quantity
                    else:
                        plans[self._normalize_name(line.employee_id.name)] = line.quantity
                elif line.target_code:
                    plans[self._normalize_code(line.target_code)] = line.quantity
            if plans:
                return plans

        if str(summary.month) != '5' or str(summary.year) != '2026':
            return {}
        team_name = team.report_name if team.report_name in self.MAY_2026_EMPLOYEE_PLANS else team.name
        name_plans = self.MAY_2026_EMPLOYEE_PLANS.get(team_name, {})
        if not name_plans:
            return {}

        plans = dict(name_plans)
        matched_employees = self.env['hr.employee'].search([]).filtered(
            lambda employee: any(
                self._normalize_name(employee.name) == planned_name
                or self._normalize_name(employee.name).endswith(' - ' + planned_name)
                for planned_name in name_plans
            )
        )
        code_counts = {}
        for employee in matched_employees:
            employee_code = self._normalize_code(employee.code)
            if employee_code:
                code_counts[employee_code] = code_counts.get(employee_code, 0) + 1

        for employee in matched_employees:
            employee_code = self._normalize_code(employee.code)
            if not employee_code or code_counts.get(employee_code) != 1:
                continue
            employee_name = self._normalize_name(employee.name)
            for planned_name, planned_quantity in name_plans.items():
                if employee_name == planned_name or employee_name.endswith(' - ' + planned_name):
                    plans[employee_code] = planned_quantity
                    break
        return plans

    def _get_employee_plan(self, employee, employee_plans):
        employee_code = self._normalize_code(employee.code)
        if employee_code and employee_code in employee_plans:
            return True, employee_plans[employee_code]

        employee_name = self._normalize_name(employee.name)
        for planned_employee_name, planned_quantity in employee_plans.items():
            if (
                employee_name == planned_employee_name
                or employee_name.endswith(' - ' + planned_employee_name)
            ):
                return True, planned_quantity
        return False, 0.0

    def _is_may_2026_no_sales_discount_employee(self, summary, employee):
        if str(summary.month) != '5' or str(summary.year) != '2026':
            return False
        employee_name = self._normalize_name(employee.name)
        return any(
            employee_name == name or employee_name.endswith(' - ' + name)
            for name in self.MAY_2026_NO_SALES_DISCOUNT_EMPLOYEES
        )

    @staticmethod
    def _normalize_code(value):
        return (value or '').strip().lower()

    @staticmethod
    def _normalize_name(value):
        value = unicodedata.normalize('NFKD', value or '')
        value = ''.join(character for character in value if not unicodedata.combining(character))
        value = value.replace('đ', 'd').replace('Đ', 'D')
        return ' '.join(value.lower().split())

    def _append_ss_employee_lines(self, summary, team, vals_list, ss_employee_ids):
        if not ss_employee_ids:
            return

        ss_commission_lines = summary.sales_commission_employee_ids.filtered(
            lambda line: line.employee_id.id in ss_employee_ids
        )
        if not ss_commission_lines:
            return

        team_revenue_lines = summary.line_ids.detail_line_ids.filtered(
            lambda line: line.line_type == 'revenue'
            and line.team_id == team
            and line.unit_price > 0
        )
        all_revenue_lines = summary.line_ids.detail_line_ids.filtered(
            lambda line: line.line_type == 'revenue'
            and line.unit_price > 0
        )

        for ss_line in ss_commission_lines:
            employee = ss_line.employee_id
            sale_user_ids = self.env['salary.sales.commission.employee']._get_employee_sale_users(employee).ids
            if not sale_user_ids:
                continue

            team_employee_lines = team_revenue_lines.filtered(
                lambda line: any(user_id in sale_user_ids for user_id in line.sale_order_ids.mapped('user_id.id'))
            )
            team_quantity = sum(team_employee_lines.mapped('quantity'))
            if not team_quantity:
                continue

            employee_lines = all_revenue_lines.filtered(
                lambda line: any(user_id in sale_user_ids for user_id in line.sale_order_ids.mapped('user_id.id'))
            )
            total_quantity = sum(employee_lines.mapped('quantity'))
            allocation_rate = team_quantity / total_quantity if total_quantity else 0.0

            vals_list.append({
                'summary_id': summary.id,
                'team_id': team.id,
                'employee_id': employee.id,
                'job_title': 'KD.SS',
                'role_sequence': 15,
                'actual_quantity': team_quantity,
                'allocation_rate': allocation_rate,
                'sales_discount_80': ss_line.amount_80 * allocation_rate,
                'humic_discount_80': 0.0,
                'sales_discount_20': ss_line.amount_20 * allocation_rate,
                'humic_discount_20': 0.0,
            })

    def _get_ss_employee_ids(self):
        return self.env['salary.sales.commission.employee']._get_ss_commission_employees().ids

    def _should_skip_employee_for_summary(self, summary, employee):
        if str(summary.month) in ('5', '6') and str(summary.year) == '2026':
            employee_name = (employee.name or '').lower()
            return 'châu kim quy' in employee_name or 'chau kim quy' in employee_name
        return False
