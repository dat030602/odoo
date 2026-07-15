from odoo import models, fields, api
from datetime import datetime, timedelta
from calendar import monthrange
from odoo.fields import Command
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SalarySalesSummary(models.Model):
    _name = 'salary.sales.summary'
    _description = 'Salary Sales Summary'

    name = fields.Char(string='Tên')
    month = fields.Selection(string='Tháng', selection=[
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'), ('4', 'Tháng 4'), 
        ('5', 'Tháng 5'), ('6', 'Tháng 6'), ('7', 'Tháng 7'), ('8', 'Tháng 8'), 
        ('9', 'Tháng 9'), ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12')
    ], default=str(datetime.now().month))
    year = fields.Integer(string='Năm', default=datetime.now().year)
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    # Field để chọn team áp dụng tỷ lệ hoa hồng
    team_id = fields.Many2one(
        'crm.team', 
        string='Khu vực áp dụng',
        required=True,
        default=lambda self: self.env['crm.team'].browse(14),
        help='Chọn khu vực để áp dụng tỷ lệ hoa hồng từ Setup tỷ lệ hoa hồng'
    )
    price_unit_commercial = fields.Monetary(string='Giá đơn vị thương mại', default=22000)
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)
    
    # Line details
    line_ids = fields.One2many(
        string='Chi tiết', 
        comodel_name='salary.sales.summary.line', 
        inverse_name='summary_id'
    )
    
    # Commission details
    commission_ids = fields.One2many(
        string='Hoa hồng khu vực', 
        comodel_name='salary.sales.commission', 
        inverse_name='summary_id'
    )
    
    employee_commission_ids = fields.One2many(
        string='Hoa hồng nhân viên', 
        comodel_name='salary.employee.commission', 
        inverse_name='summary_id'
    )
    
    personnel_commission_ids = fields.One2many(
        string='Hoa hồng nhân sự khu vực', 
        comodel_name='salary.personnel.commission', 
        inverse_name='summary_id'
    )
    
    bonus_commission_ids = fields.One2many(
        string='Hoa hồng thưởng thêm', 
        comodel_name='salary.bonus.commission', 
        inverse_name='summary_id'
    )
    
    sales_commission_employee_ids = fields.One2many(
        string='Hoa hồng nhân viên phòng kinh doanh', 
        comodel_name='salary.sales.commission.employee', 
        inverse_name='summary_id'
    )
    
    humic_sales_detail_ids = fields.One2many(
        string='Chi tiết bán hàng sản phẩm humic', 
        comodel_name='salary.humic.sales.detail', 
        inverse_name='summary_id'
    )
    
    customer_open_list_ids = fields.One2many(
        string='Danh sách khách hàng mở', 
        comodel_name='salary.customer.open.list', 
        inverse_name='summary_id'
    )
    
    commission_result_ids = fields.One2many(
        string='Kết quả tính toán hoa hồng', 
        comodel_name='salary.commission.result', 
        inverse_name='summary_id'
    )
    
    commercial_discount_detail_ids = fields.One2many(
        string='Chiết khấu thương mại',
        comodel_name='salary.commercial.discount.detail',
        inverse_name='summary_id'
    )

    # Aggregated totals ignoring states (per team)
    total_line_ids = fields.One2many(
        string='Tổng hợp theo khu vực',
        comodel_name='salary.sales.summary.total.line',
        inverse_name='summary_id'
    )

    voter_id = fields.Many2one('res.users',string="Người lập")
    chief_finance_id = fields.Many2one('res.users',string="Phòng Kế toán")
    lead_sale_id = fields.Many2one('res.users',string="Phòng Kinh doanh")
    director_id  = fields.Many2one('res.users',string="Thủ trưởng đơn vị")
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(SalarySalesSummary, self).default_get(fields_list)

        env_params = self.env['ir.config_parameter'].sudo()
        chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
        director_id = env_params.get_param('ccv_bao_cao.director_id', False)
        lead_sale_id = env_params.get_param('ccv_bao_cao_cong_no.lead_sale_id', False)
        
        defaults.update({
            'voter_id': self.env.user.id,
            'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
            'lead_sale_id': int(lead_sale_id) if lead_sale_id else False,
            'director_id': int(director_id) if director_id else False,
        })
        return defaults

    @api.onchange('year', 'month')
    def _onchange_year_month(self):
        for rec in self:
            if rec.year and rec.month:
                rec.name = f'Bảng hoa hồng {rec.month}/{rec.year}'

    state = fields.Selection(string='Trạng thái', selection=[('draft', 'Nháp'), ('done', 'Hoàn thành')], default='draft')

    def action_done(self):
        self.ensure_one()
        self.state = 'done'

    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'
    
    def unlink(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError('Không thể xóa tổng hợp đã hoàn thành')
        return super(SalarySalesSummary, self).unlink()

    def _get_date_range(self):
        year = int(self.year)
        month = int(self.month)
        first_day = datetime(year, month, 1, 0, 0, 0)
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59)
        return first_day, last_day
    
    def action_get_data(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.commission_ids.unlink()
        self.employee_commission_ids.unlink()
        self.personnel_commission_ids.unlink()
        self.bonus_commission_ids.unlink()
        self.sales_commission_employee_ids.unlink()
        self.humic_sales_detail_ids.unlink()
        self.customer_open_list_ids.unlink()
        self.commission_result_ids.unlink()
        self.total_line_ids.unlink()
        self.commercial_discount_detail_ids.unlink()

        date_from, date_to = self._get_date_range()
        stock_move_env = self.env['stock.move'].with_context(lang='vi_VN')
        aml_env = self.env['account.move.line'].with_context(lang='vi_VN')
        salary_plan_sales_env = self.env['salary.plan.sales'].with_context(lang='vi_VN')

        sms = stock_move_env.search([
            ('sale_line_id', '!=', False),
            ('sale_line_id.is_promotional_product', '=', False),
            ('state', '=', 'done'),
            ('date', '>=', (date_from - timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')),
            ('date', '<=', (date_to - timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')),
            '|',
            ('location_id.usage', '=', 'customer'),
            ('location_dest_id.usage', '=', 'customer')
        ])
        amls = aml_env.browse([aml[0] for aml in self._get_aml(date_from, date_to)])

        team_ids = sms.mapped('picking_id.sale_id.team_id')
        src_line_ids = self.line_ids
        # Khởi tạo dữ liệu
        for team_id in team_ids:
            states = sms.filtered(lambda sm: sm.picking_id.sale_id.team_id == team_id).mapped('picking_id.partner_id.state_id')
            states |= amls.filtered(lambda aml: aml.partner_id.team_id == team_id).mapped('partner_id.state_id')
            state_line_ids = salary_plan_sales_env.search([('team_id', '=', team_id.id), ('month', '=', self.month), ('year', '=', self.year)], limit=1).line_ids
            states |= state_line_ids.state_ids
            # Tính toán planned_quantity cho từng state
            # Lấy quantity từ state_ids có state_ids chứa state tương ứng
            state_planned_quantities = {}

            # Khởi tạo dòng kế hoạch với state được cài đặt
            for state_line in state_line_ids:
                planned_quantity = state_line.quantity / (len(state_line.state_ids) or 1)
                for state in state_line.state_ids:
                    state_planned_quantities[state] = state_planned_quantities.get(state, 0) + planned_quantity
            
            # Khởi tạo dòng kế hoạch với state không được set
            non_state_line_ids = state_line_ids.filtered(lambda line: not line.state_ids)
            non_state_ids = states - state_line_ids.state_ids
            planned_quantity = sum(non_state_line_ids.mapped('quantity')) / (len(non_state_ids) or 1)
            for state in non_state_ids:
                state_planned_quantities[state] = state_planned_quantities.get(state, 0) + planned_quantity
            for state in states:
                planned_quantity = state_planned_quantities.get(state, 0)
                src_line_ids |= self.line_ids.create({
                    'summary_id': self.id,
                    'state_id': state.id,
                    'team_id': team_id.id,
                    'planned_quantity': planned_quantity,
                })
            src_line_ids |= self.line_ids.create({
                'summary_id': self.id,
                'state_id': False,
                'team_id': team_id.id,
                'planned_quantity': 0,
            })

            # Chỉ xử lý các dòng thuộc team_id hiện tại
            current_team_line_ids = src_line_ids.filtered(lambda line: line.team_id == team_id)

            # Tính toán doanh thu
            for src_line_id in current_team_line_ids:
                cur_sms = sms.filtered(lambda sm: sm.picking_id.sale_id.team_id == team_id and sm.picking_id.sale_id.order_state_id == src_line_id.state_id)
                line_vals = src_line_id._prepare_revenue_line_from_stock_move(self.id, cur_sms, date_from, date_to)
                src_line_id.write({'detail_line_ids': [Command.create(line_val) for line_val in line_vals]})

            # Tính toán Doanh thu tiền về
            for src_line_id in current_team_line_ids:
                cur_amls = amls.filtered(lambda aml: aml.partner_id.team_id == team_id and aml.partner_id.state_id == src_line_id.state_id)
                line_vals = src_line_id._prepare_payment_line_from_aml(cur_amls)
                src_line_id.write({'detail_line_ids': [Command.create(line_val) for line_val in line_vals]})
            
            # Tính toán Xuất hóa đơn trước
            for src_line_id in current_team_line_ids:
                cur_sms = sms.filtered(lambda sm: sm.picking_id.sale_id.team_id == team_id and sm.picking_id.sale_id.order_state_id == src_line_id.state_id)
                for cur_sm in cur_sms:
                    if cur_sm.location_id.usage == 'customer':
                        continue
                    
                    inv_amls = cur_sm.sale_line_id.invoice_lines
                    if not inv_amls:
                        continue

                    quantity = cur_sm.quantity_done

                    # Nếu trong tháng thì bỏ qua
                    aml_this_month = inv_amls.filtered(lambda aml: aml.move_id.date >= date_from.date() and aml.move_id.date <= date_to.date())
                    quantity -= sum(aml_this_month.mapped('quantity'))
                    if quantity <= 0:
                        continue

                    # Nếu trước tháng thì add
                    aml_pre_month = inv_amls.filtered(lambda aml: aml.move_id.date < date_from.date())
                    quantity -= sum(aml_pre_month.mapped('quantity'))
                    if quantity <= 0:
                        line_vals = src_line_id._prepare_invoice_line_from_invoice(self.id, cur_sm, aml_pre_month.move_id)
                        src_line_id.write({'detail_line_ids': [Command.create(line_val) for line_val in line_vals]})


        # Build/refresh total lines per team (across states)
        total_records_vals = []
        for team in self.line_ids.mapped('team_id'):
            total_records_vals.append((0, 0, {
                'summary_id': self.id,
                'team_id': team.id,
            }))
        if total_records_vals:
            self.write({'total_line_ids': total_records_vals})
        
        # Tạo dữ liệu hoa hồng sau khi có dữ liệu tổng hợp
        self._create_commission_data()
        self._create_personnel_commission_data()
        self._create_bonus_commission_data()
        self._create_sales_commission_employee_data()
        self._create_humic_sales_detail_data()
        self._create_commercial_discount_detail_data()
        self._create_customer_open_list_data()
        self._create_commission_result_data()

    def _create_commercial_discount_detail_data(self):
        """Tạo dữ liệu chiết khấu thương mại"""
        self.ensure_one()
        
        # Tạo dữ liệu từ summary data
        self.commercial_discount_detail_ids.unlink()
        self.env['salary.commercial.discount.detail'].create({
            'summary_id': self.id,
        })

    def _get_aml(self, date_start, date_end, partner_ids=[]):
        # Build the SELECT clause
        account_id = self.env['account.account'].search([('code', '=', '13111')]).id
        sql = """
            SELECT aml.id, abs(aml.balance) as balance
        """
        
        # Add FROM and WHERE clauses
        sql += """
            FROM account_move_line aml
            RIGHT JOIN account_move am ON am.id = aml.move_id
            WHERE am.state = 'posted'
              AND aml.company_id = %s
              AND aml.account_id = %s
              AND aml.balance < 0
        """
        
        params = [self.env.company.id, account_id]

        sql += " AND am.date >= %s AND am.date <= %s"
        params.extend([date_start.strftime("%Y%m%d"), date_end.strftime("%Y%m%d")])

        if partner_ids:
            placeholders = ','.join(['%s'] * len(partner_ids))
            sql += f" AND aml.partner_id IN ({placeholders})"
            params.extend(partner_ids)

        self._cr.execute(sql, tuple(params))
        return self._cr.fetchall()

    def _create_commission_data(self):
        """Tạo dữ liệu hoa hồng cho các khu vực"""
        self.ensure_one()
        
        # Xóa dữ liệu cũ
        self.commission_ids.unlink()
        self.employee_commission_ids.unlink()
        
        # Lấy danh sách các team có dữ liệu
        team_ids = self.line_ids.mapped('team_id')
        
        # Tạo hoa hồng cho từng khu vực
        commission_vals = []
        employee_commission_vals = []
        
        for team_id in team_ids:
            # Tạo commission record
            # Tìm total_line tương ứng khu vực
            total_line = self.total_line_ids.filtered(lambda tl: tl.team_id == team_id)[:1]
            commission_record = self.env['salary.sales.commission'].create({
                'summary_id': self.id,
                'team_id': team_id.id,
                'total_line_id': total_line.id if total_line else False,
            })
            commission_vals.append(commission_record.id)
            
            # Tạo employee commission record
            employee_commission_record = self.env['salary.employee.commission'].create({
                'commission_id': commission_record.id,
            })
            employee_commission_vals.append(employee_commission_record.id)
        
        # Cập nhật One2many fields
        self.write({
            'commission_ids': [(6, 0, commission_vals)],
            'employee_commission_ids': [(6, 0, employee_commission_vals)],
        })

    def _create_personnel_commission_data(self):
        """Tạo dữ liệu hoa hồng nhân sự khu vực"""
        self.ensure_one()
        
        # Xóa dữ liệu cũ
        self.personnel_commission_ids.unlink()
        
        # Lấy danh sách các team có dữ liệu
        team_ids = self.line_ids.mapped('team_id')
        
        # Tạo personnel commission cho từng khu vực
        personnel_commission_vals = []
        
        for team_id in team_ids:
            personnel_commission_record = self.env['salary.personnel.commission'].create({
                'summary_id': self.id,
                'team_id': team_id.id,
            })
            personnel_commission_vals.append(personnel_commission_record.id)
        
        # Cập nhật One2many field
        self.write({
            'personnel_commission_ids': [(6, 0, personnel_commission_vals)],
        })

    def _create_bonus_commission_data(self):
        """Tạo dữ liệu hoa hồng thưởng thêm theo doanh số"""
        self.ensure_one()
        
        # Xóa dữ liệu cũ
        self.bonus_commission_ids.unlink()
        
        # Lấy danh sách các team có dữ liệu
        team_ids = self.line_ids.mapped('team_id')
        
        # Tạo bonus commission cho từng khu vực
        bonus_commission_vals = []
        
        for team_id in team_ids:
            bonus_commission_record = self.env['salary.bonus.commission'].create({
                'summary_id': self.id,
                'team_id': team_id.id,
            })
            bonus_commission_vals.append(bonus_commission_record.id)
        
        # Cập nhật One2many field
        self.write({
            'bonus_commission_ids': [(6, 0, bonus_commission_vals)],
        })

    def _create_sales_commission_employee_data(self):
        """Tạo dữ liệu hoa hồng nhân viên phòng kinh doanh"""
        self.ensure_one()
        
        # Xóa dữ liệu cũ
        self.sales_commission_employee_ids.unlink()
        
        # Tạo mặc định cho 3 nhân viên phòng kinh doanh
        self.env['salary.sales.commission.employee'].create_default_employees(self.id)

    def _create_humic_sales_detail_data(self):
        """Tạo dữ liệu chi tiết bán hàng sản phẩm humic"""
        self.ensure_one()
        
        # Tạo dữ liệu từ summary detail lines
        self.env['salary.humic.sales.detail'].create_from_summary_detail_lines(self.id)

    def _create_customer_open_list_data(self):
        """Tạo dữ liệu danh sách khách hàng mở"""
        self.ensure_one()
        
        # Xóa dữ liệu cũ
        self.customer_open_list_ids.unlink()
        
        # Tạo dữ liệu từ summary data
        self.env['salary.customer.open.list'].create_from_summary_data(self.id)

    def _create_commission_result_data(self):
        """Tạo dữ liệu kết quả tính toán hoa hồng"""
        self.ensure_one()
        
        # Xóa dữ liệu cũ
        self.commission_result_ids.unlink()
        
        # Tính toán tất cả hoa hồng
        commission_calculation_env = self.env['salary.commission.calculation']
        results = commission_calculation_env.calculate_all_commissions(self.id)
        
        if not results:
            return
        
        # Tạo dữ liệu kết quả cho từng nhân viên
        results_data = {}
        combined_results = {}
        
        for key, result_data in results.items():
            if result_data.get('is_combined'):
                # Lưu combined results để xử lý riêng
                combined_results[key] = {
                    'amount': result_data['amount'],
                    'individual_calc_ids': result_data.get('individual_calc_ids', []),
                    'note': f"Tổng hợp từ {len(result_data.get('individual_calc_ids', []))} công thức"
                }
            elif result_data.get('is_individual'):
                # Tạo dữ liệu cho từng nhân viên
                calc_id = key
                calculation = self.env['salary.commission.calculation'].browse(calc_id)
                
                if not calculation.exists():
                    continue
                
                # Lấy danh sách nhân viên áp dụng
                employee_ids = calculation.employee_ids
                
                if calc_id not in results_data:
                    results_data[calc_id] = {}
                
                if not employee_ids:
                    # Nếu không có nhân viên cụ thể, tạo record với employee_id null
                    results_data[calc_id][False] = {
                        'amount': result_data['amount'],
                    }
                else:
                    # Chia đều số tiền cho tất cả nhân viên
                    total_amount = result_data['amount']
                    employee_count = len(employee_ids)
                    amount_per_employee = total_amount / employee_count if employee_count > 0 else 0
                    
                    for employee_id in employee_ids:
                        results_data[calc_id][employee_id.id] = {
                            'amount': amount_per_employee,
                        }
        
        # Tạo commission result records
        commission_result_env = self.env['salary.commission.result']
        commission_result_env.create_commission_results(self.id, results_data)

    def recalculate_commission_data(self):
        self._create_commission_result_data()

    # Action helpers for stat buttons in button_box
    def _act_open(self, name, model, domain, search_default_group_team=False, search_default_group_type=False, search_default_group_employee=False):
        self.ensure_one()
        ctx = {}
        if search_default_group_team:
            ctx['search_default_group_team'] = 1
        if search_default_group_type:
            ctx['search_default_group_type'] = 1
        if search_default_group_employee:
            ctx['search_default_group_employee'] = 1
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'tree',
            'domain': domain,
            'context': ctx,
            'target': 'current',
        }

    def action_open_summary_lines(self):
        return self._act_open('Chi tiết tổng hợp', 'salary.sales.summary.line', [('summary_id', '=', self.id)], search_default_group_team=True)

    def action_open_commissions(self):
        return self._act_open('Hoa hồng khu vực', 'salary.sales.commission', [('summary_id', '=', self.id)], search_default_group_team=True)

    def action_open_employee_commissions(self):
        return self._act_open('Hoa hồng nhân viên', 'salary.employee.commission', [('commission_id.summary_id', '=', self.id)], search_default_group_team=True)

    def action_open_personnel_commissions(self):
        return self._act_open('Hoa hồng nhân sự khu vực', 'salary.personnel.commission', [('summary_id', '=', self.id)], search_default_group_team=True)

    def action_open_bonus_commissions(self):
        return self._act_open('Hoa hồng thưởng thêm', 'salary.bonus.commission', [('summary_id', '=', self.id)], search_default_group_team=True)

    def action_open_sales_commission_employee(self):
        return self._act_open('Hoa hồng NV phòng kinh doanh', 'salary.sales.commission.employee', [('summary_id', '=', self.id)], search_default_group_team=False)

    def action_open_humic_sales_detail(self):
        return self._act_open('Chi tiết bán hàng humic', 'salary.humic.sales.detail', [('summary_id', '=', self.id)], search_default_group_team=True)

    def action_open_customer_open_list(self):
        return self._act_open('Danh sách khách hàng mở', 'salary.customer.open.list', [('summary_id', '=', self.id)], search_default_group_team=True)

    def action_open_commission_results(self):
        return self._act_open('Kết quả tính toán hoa hồng', 'salary.commission.result', [('summary_id', '=', self.id)], search_default_group_employee=True)

    def action_create_default_employees(self):
        """Action để tạo lại 3 nhân viên phòng kinh doanh mặc định"""
        self.ensure_one()
        self._create_sales_commission_employee_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def push_salary_to_allowance(self):
        """Đẩy lương vào hr.allowance với code = LKPIDSHH"""
        self.ensure_one()
        
        HrContract = self.env['hr.contract'].sudo()
        HrAllowance = self.env['hr.allowance'].sudo()
        
        year = int(self.year)
        month = str(int(self.month))
        code = 'CT'
        
        # Lấy tất cả commission results có số tiền > 0
        commission_results = self.commission_result_ids.filtered(lambda x: x.amount > 0 and x.employee_id)
        
        if not commission_results:
            return
        
        # Nhóm theo employee_id
        employee_results = {}
        for result in commission_results:
            if result.employee_id.id not in employee_results:
                employee_results[result.employee_id.id] = 0
            employee_results[result.employee_id.id] += result.amount
        
        # Đẩy hoa hồng cho từng nhân viên
        for employee_id, total_amount in employee_results.items():
            date_from, date_to = self._get_date_range()
            contracts = HrContract.search([
                ('employee_id', '=', employee_id),
                ('date_start', '<=', date_to),
                '|', 
                ('date_end', '=', False),
                ('date_end', '>=', date_from),
            ])
            
            for contract in contracts:
                allowance_month = contract.allowance_month_ids.filtered(lambda x: x.year == year and x.month == month and x.code == code)
                if allowance_month:
                    allowance_month.unlink()
                allowance_id = HrAllowance.search([('code', '=', code)], limit=1)
                if not allowance_id:
                    allowance_id = HrAllowance.create({
                        'name': 'Hoa hồng thưởng',
                        'code': code,
                        'is_fixed': False
                    })
                
                # Tạo allowance_month record
                allowance_month_vals = {
                    'amount': total_amount,
                    'allowance_id': allowance_id.id,
                    'year': year,
                    'month': month,
                    'code': code
                }
                contract.allowance_month_ids = [(0, 0, allowance_month_vals)]
