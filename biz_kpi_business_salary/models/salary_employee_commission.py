from odoo import models, fields, api

class SalaryEmployeeCommission(models.Model):
    """Bảng Hoa hồng nhân viên các phòng ban"""
    _name = 'salary.employee.commission'
    _description = 'Salary Employee Commission'
    _order = 'sequence, team_id, id'

    ITEM_NAMES = [
        'Khu vực 1',
        'Khu vực 2',
        'Khu vực 3',
        'Khu vực 4',
        'Khu vực 5',
        'Phòng thương mại',
        'Bán hàng Online',
        'Ban lãnh đạo',
        'Khối bán hàng',
        'Phòng ban khác',
        'Quỹ thưởng',
    ]

    name = fields.Char(string='Khoản mục', compute='_compute_name', store=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    item_name = fields.Char(string='Khoản mục', required=True)
    summary_id = fields.Many2one('salary.sales.summary', string='Tổng hợp doanh thu', required=True, ondelete='cascade')
    commission_id = fields.Many2one('salary.sales.commission', string='Hoa hồng khu vực', ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Khu vực')
    active = fields.Boolean(string='Kích hoạt', related='summary_id.active')
    total_amount_80 = fields.Monetary(string='Tổng nhận 80%')
    total_amount_20 = fields.Monetary(string='Tổng giữ lại 20%')
    total_amount = fields.Monetary(string='Tổng cộng', compute='_compute_total_amount', store=True)

    # Backward-compatible fields used by old reports.
    team_commission = fields.Monetary(string='Thưởng khu vực')
    leadership_commission = fields.Monetary(string='Ban Lãnh Đạo')
    department_commission = fields.Monetary(string='Các Phòng Ban')
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.depends('item_name')
    def _compute_name(self):
        for record in self:
            record.name = record.item_name or ''

    @api.depends('total_amount_80', 'total_amount_20')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.total_amount_80 + record.total_amount_20

    @api.model
    def create_from_summary_tabs(self, summary_id):
        if not summary_id:
            return False

        summary = self.env['salary.sales.summary'].browse(summary_id)
        if not summary.exists():
            return False

        self.search([('summary_id', '=', summary.id)]).unlink()
        vals_list = []

        for sequence, item_name in enumerate(self.ITEM_NAMES, start=1):
            vals = {
                'summary_id': summary.id,
                'sequence': sequence * 10,
                'item_name': item_name,
            }
            team = self._find_team_by_name(item_name) if item_name.startswith('Khu vực ') else self.env['crm.team']
            if team:
                vals['team_id'] = team.id
                personnel_lines = summary.personnel_commission_ids.filtered(lambda line: line.team_id == team)
                vals['total_amount_80'] = sum(personnel_lines.mapped('total_amount_80'))
                vals['total_amount_20'] = sum(personnel_lines.mapped('total_amount_20'))
                vals['team_commission'] = vals['total_amount_80']
            else:
                sales_lines = self._filter_lines_by_name(summary.sales_discount_ids, item_name)
                humic_lines = self._filter_lines_by_name(summary.humic_discount_ids, item_name)
                vals['total_amount_80'] = sum(sales_lines.mapped('amount_80')) + sum(humic_lines.mapped('amount_80'))
                vals['total_amount_20'] = sum(sales_lines.mapped('amount_20')) + sum(humic_lines.mapped('amount_20'))
                if item_name == 'Ban lãnh đạo':
                    vals['leadership_commission'] = vals['total_amount_80']
                elif item_name in ['Phòng ban khác', 'Phòng thương mại', 'Bán hàng Online']:
                    vals['department_commission'] = vals['total_amount_80']

            vals_list.append(vals)

        return self.create(vals_list) if vals_list else False

    def _filter_lines_by_name(self, lines, item_name):
        item_name_lower = (item_name or '').lower()
        return lines.filtered(lambda line: (line.name or '').lower() == item_name_lower)

    def _find_team_by_name(self, team_name):
        return self.env['crm.team'].search([
            '|',
            ('report_name', '=', team_name),
            ('name', '=', team_name),
        ], limit=1)

    def action_view_commission_details(self):
        """Action để xem chi tiết hoa hồng khu vực"""
        self.ensure_one()
        if not self.commission_id:
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Hoa hồng khu vực {self.team_id.name}',
            'res_model': 'salary.sales.commission',
            'res_id': self.commission_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
