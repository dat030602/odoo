import unicodedata

from odoo import models, fields, api


class SalarySalesSummaryTotalLine(models.Model):
    """Aggregated totals per team across all states for a given summary"""
    _name = 'salary.sales.summary.total.line'
    _description = 'Salary Sales Summary Total Line'
    _order = 'team_id'

    MAY_2026_TEAM_PLANS = {
        'Khu vực 1': {'old_customer_plan_quantity': 1734.3, 'new_customer_plan_quantity': 192.7},
        'Khu vực 2': {'old_customer_plan_quantity': 922.0, 'new_customer_plan_quantity': 102.0},
        'Khu vực 3': {'old_customer_plan_quantity': 976.0, 'new_customer_plan_quantity': 108.0},
        'Khu vực 4': {'old_customer_plan_quantity': 1345.5, 'new_customer_plan_quantity': 149.5},
        'Khu vực 5': {'old_customer_plan_quantity': 1411.2, 'new_customer_plan_quantity': 156.8},
    }

    name = fields.Char(string='Tên', related='team_id.report_name')
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực', required=True)
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')

    # Totals aggregated from salary.sales.summary.line by team
    old_customer_plan_quantity = fields.Float(string='Kế hoạch khách hàng cũ', digits="Product Unit of Measure", compute='_compute_totals', store=True)
    new_customer_plan_quantity = fields.Float(string='Kế hoạch khách hàng mới', digits="Product Unit of Measure", compute='_compute_totals', store=True)
    planned_quantity = fields.Float(string='Kế hoạch', digits="Product Unit of Measure", compute='_compute_totals', store=True)
    production_quantity = fields.Float(string='Sản lượng', digits="Product Unit of Measure", compute='_compute_totals', store=True)
    old_customer_actual_quantity = fields.Float(string='Thực hiện OC', digits="Product Unit of Measure", compute='_compute_totals', store=True)
    new_customer_actual_quantity = fields.Float(string='Thực hiện NC', digits="Product Unit of Measure", compute='_compute_totals', store=True)
    total_revenue = fields.Monetary(string='Doanh thu', compute='_compute_totals', store=True)
    total_payment_received = fields.Monetary(string='Doanh thu tiền về', compute='_compute_totals', store=True)
    total_invoice_amount = fields.Monetary(string='Xuất HĐ trước', compute='_compute_totals', store=True)
    total_invoice_quantity = fields.Float(string='Số lượng xuất HĐ trước', compute='_compute_totals', store=True)

    # Rates follow existing formulas on detail lines
    achievement_rate = fields.Float(string='Tỷ lệ (%)', compute='_compute_rates', store=True)
    old_customer_rate = fields.Float(string='Tỷ lệ OC', compute='_compute_rates', store=True)
    new_customer_rate = fields.Float(string='Tỷ lệ NC', compute='_compute_rates', store=True)
    progress_compensation_rate = fields.Float(string='Tỷ lệ bù tiến', compute='_compute_rates', store=True)
    total_rate = fields.Float(string='Tổng tỷ lệ', compute='_compute_rates', store=True)
    payment_rate = fields.Float(string='Tỷ lệ thanh toán (%)', compute='_compute_rates', store=True)

    is_apply_pre_invoice = fields.Boolean(string='Áp dụng xuất HĐ trước', default=False)

    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    # Đơn giá chiết khấu (nhập tay theo tháng từng khu vực)
    discount_price_oc = fields.Monetary(
        string='Đơn giá CK OC (đ/tấn)',
        default=30000,
        help='Đơn giá chiết khấu cho khách hàng cũ (OC). Áp dụng khi đạt ≥90% kế hoạch.'
    )
    discount_price_nc = fields.Monetary(
        string='Đơn giá CK NC (đ/tấn)',
        default=40000,
        help='Đơn giá chiết khấu cho khách hàng mới (NC). Áp dụng khi đạt >100% kế hoạch.'
    )
    discount_price_humic_bag = fields.Monetary(
        string='Đơn giá CK Humic bao lớn (đ/tấn)',
        default=80000,
        help='Đơn giá chiết khấu Humic Acid / K-Humate bao lớn bán sỉ.'
    )
    discount_price_humic_small = fields.Monetary(
        string='Đơn giá CK Humic túi nhỏ (đ/tấn)',
        default=3000,
        help='Đơn giá chiết khấu Humic túi 1kg.'
    )

    @api.depends('summary_id.line_ids.team_id',
                 'summary_id.line_ids.planned_quantity',
                 'summary_id.line_ids.production_quantity',
                 'summary_id.line_ids.total_revenue',
                 'summary_id.line_ids.total_payment_received',
                 'summary_id.line_ids.total_invoice_amount',
                 'summary_id.customer_open_list_ids.partner_id.team_id',
                 'summary_id.customer_open_list_ids.quantity')
    def _compute_totals(self):
        for record in self:
            lines = record.summary_id.line_ids.filtered(lambda l: l.team_id == record.team_id)
            customer_open_lines = record.summary_id.customer_open_list_ids.filtered(
                lambda line: line.team_id == record.team_id
            )
            
            # Ưu tiên lấy từ Kế hoạch khai báo động trên Odoo
            plan = self.env['salary.plan.sales'].search([
                ('team_id', '=', record.team_id.id),
                ('month', '=', record.summary_id.month),
                ('year', '=', record.summary_id.year)
            ], limit=1)
            
            if plan:
                oc_lines = plan.line_ids.filtered(lambda l: l.target_type == 'oc')
                nc_lines = plan.line_ids.filtered(lambda l: l.target_type == 'nc')
                record.old_customer_plan_quantity = sum(oc_lines.mapped('quantity'))
                record.new_customer_plan_quantity = sum(nc_lines.mapped('quantity'))
                record.planned_quantity = record.old_customer_plan_quantity + record.new_customer_plan_quantity
            else:
                # Fallback: Nếu không có kế hoạch trên Odoo, thử lấy từ code hardcode cũ (Tháng 5/2026)
                team_plan = record._get_may_2026_team_plan()
                record.old_customer_plan_quantity = team_plan.get('old_customer_plan_quantity', 0.0)
                record.new_customer_plan_quantity = team_plan.get('new_customer_plan_quantity', 0.0)
                if team_plan:
                    record.planned_quantity = record.old_customer_plan_quantity + record.new_customer_plan_quantity
                else:
                    record.planned_quantity = sum(lines.mapped('planned_quantity'))
            record.production_quantity = sum(lines.mapped('production_quantity'))
            record.new_customer_actual_quantity = sum(customer_open_lines.mapped('quantity'))
            record.old_customer_actual_quantity = (
                record.production_quantity - record.new_customer_actual_quantity
            )
            record.total_revenue = sum(lines.mapped('total_revenue'))
            record.total_payment_received = sum(lines.mapped('total_payment_received'))
            record.total_invoice_amount = sum(lines.mapped('total_invoice_amount'))
            record.total_invoice_quantity = sum(lines.mapped('total_invoice_quantity'))

    def _get_may_2026_team_plan(self):
        self.ensure_one()
        if str(self.summary_id.month) != '5' or str(self.summary_id.year) != '2026':
            return {}
        team_name = self.team_id.report_name if self.team_id.report_name in self.MAY_2026_TEAM_PLANS else self.team_id.name
        return self.MAY_2026_TEAM_PLANS.get(team_name, {})

    def get_sales_discount_achievement_rate(self):
        """Return the approved rate used to calculate ASM/team sales discount."""
        self.ensure_one()
        if self._is_may_2026_team_5():
            return 0.70
        return max(self.achievement_rate, self.new_customer_rate)

    def _is_may_2026_team_5(self):
        self.ensure_one()
        if str(self.summary_id.month) != '5' or str(self.summary_id.year) != '2026':
            return False
        team_name = self.team_id.report_name or self.team_id.name or ''
        normalized_name = unicodedata.normalize('NFKD', team_name)
        normalized_name = ''.join(
            character for character in normalized_name
            if not unicodedata.combining(character)
        ).lower().strip()
        return normalized_name in ('khu vuc 5', 'kv 5', 'kv5') or normalized_name.endswith(' 5')

    @api.depends(
        'planned_quantity',
        'production_quantity',
        'old_customer_plan_quantity',
        'new_customer_plan_quantity',
        'old_customer_actual_quantity',
        'new_customer_actual_quantity',
        'total_revenue',
        'total_payment_received',
        'total_invoice_amount',
        'is_apply_pre_invoice',
        'summary_id.personnel_commission_ids.team_id',
        'summary_id.personnel_commission_ids.role_sequence',
        'summary_id.personnel_commission_ids.progress_compensation_rate',
    )
    def _compute_rates(self):
        for record in self:
            # Use same logic as original fields
            # payment_rate = total_payment_received / (total_revenue or 1), 1 if total_revenue == 0
            payment_rate = record.total_payment_received / ((record.total_revenue - (record.total_invoice_amount if not record.is_apply_pre_invoice else 0)) or 1)
            if record.total_revenue == 0:
                payment_rate = 1
            elif payment_rate < 0:
                payment_rate = 0
            record.payment_rate = payment_rate

            # achievement_rate = production_quantity / planned_quantity
            achievement_rate = record.production_quantity / (record.planned_quantity or 1)
            if record.planned_quantity == 0:
                achievement_rate = 1
            record.achievement_rate = achievement_rate
            record.old_customer_rate = (
                record.old_customer_actual_quantity / record.old_customer_plan_quantity
                if record.old_customer_plan_quantity else 0.0
            )
            record.new_customer_rate = (
                record.new_customer_actual_quantity / record.new_customer_plan_quantity
                if record.new_customer_plan_quantity else 0.0
            )

            team_leader_line = record.summary_id.personnel_commission_ids.filtered(
                lambda line: line.team_id == record.team_id and line.role_sequence == 10
            )[:1]
            record.progress_compensation_rate = (
                team_leader_line.progress_compensation_rate if team_leader_line else 0.0
            )
            record.total_rate = record.achievement_rate + record.progress_compensation_rate

    def action_view_detail_lines(self):
        """Action để mở view chi tiết các dòng"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết dòng tổng hợp',
            'res_model': 'salary.sales.summary.detail.line',
            'view_mode': 'tree',
            'domain': [('summary_id', '=', self.summary_id.id), ('team_id', '=', self.team_id.id)],
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
            'domain': [('summary_id', '=', self.summary_id.id), ('team_id', '=', self.team_id.id), ('line_type', '=', 'revenue')],
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
            'domain': [('summary_id', '=', self.summary_id.id), ('team_id', '=', self.team_id.id), ('line_type', '=', 'payment')],
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
            'domain': [('summary_id', '=', self.summary_id.id), ('team_id', '=', self.team_id.id), ('line_type', '=', 'invoice')],
            'context': {
                'default_summary_line_id': self.id,
                'default_summary_id': self.summary_id.id,
                'default_line_type': 'invoice',
            },
            'target': 'current',
        }

