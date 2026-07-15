# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BonusHistoryReportWizard(models.TransientModel):
    _inherit = 'bonus.history.report.wizard'
    _description = 'Wizard Báo cáo quỹ dự phòng'

    date_from_month = fields.Selection(string='Từ tháng', required=True, selection=[
        ('1', 'Tháng 1'),
        ('2', 'Tháng 2'),
        ('3', 'Tháng 3'),
        ('4', 'Tháng 4'),
        ('5', 'Tháng 5'),
        ('6', 'Tháng 6'),
        ('7', 'Tháng 7'),
        ('8', 'Tháng 8'),
        ('9', 'Tháng 9'),
        ('10', 'Tháng 10'),
        ('11', 'Tháng 11'),
        ('12', 'Tháng 12'),
    ])
    date_from_year = fields.Selection(string='Từ năm', required=True, selection=[
        ('2025', '2025'),
        ('2026', '2026'),
        ('2027', '2027'),
        ('2028', '2028'),
        ('2029', '2029'),
        ('2030', '2030'),
    ])
    date_to_month = fields.Selection(string='Đến tháng', required=True, selection=[
        ('1', 'Tháng 1'),
        ('2', 'Tháng 2'),
        ('3', 'Tháng 3'),
        ('4', 'Tháng 4'),
        ('5', 'Tháng 5'),
        ('6', 'Tháng 6'),
        ('7', 'Tháng 7'),
        ('8', 'Tháng 8'),
        ('9', 'Tháng 9'),
        ('10', 'Tháng 10'),
        ('11', 'Tháng 11'),
        ('12', 'Tháng 12'),
    ])
    date_to_year = fields.Selection(string='Đến năm', required=True, selection=[
        ('2025', '2025'),
        ('2026', '2026'),
        ('2027', '2027'),
        ('2028', '2028'),
        ('2029', '2029'),
        ('2030', '2030'),
    ])
    team_ids = fields.Many2many('crm.team', string='Đội bán hàng')
    
    # Các trường cho chữ ký
    voter_id = fields.Many2one('res.users', string='Người lập')
    lead_sale_id = fields.Many2one('res.users', string='Phòng Kinh doanh')
    director_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        env_params = self.env['ir.config_parameter'].sudo()
        res.update({
            'director_id': int(env_params.get_param('ccv_bao_cao_cong_no.unit_heads_id', 0)),
            'lead_sale_id': int(env_params.get_param('ccv_bao_cao_cong_no.lead_sale_id', 0)),
            'voter_id': self.env.user.id,
        })
        ctx = self.env.context
        if ctx.get('active_model') == 'sale.bonus.price.unit':
            bonus_ids = self.env['sale.bonus.price.unit'].browse(ctx.get('active_ids', []))
            res['team_ids'] = [(6, 0, bonus_ids.mapped('team_id').ids)]
        else:
            team_id = self.env['crm.team'].search([
                '|', '|',
                ('user_id','=',self.env.user.id),
                ('member_ids','in',[self.env.user.id]),
                ('sales_assistant_ids','in',[self.env.user.id]),
            ], limit=1)
            res['team_ids'] = [(6, 0, team_id.ids)]
        return res

    def action_generate_report(self):
        """
        Tạo báo cáo Excel
        """
        self.ensure_one()
        
        # Kiểm tra điều kiện
        if int(self.date_from_year) > int(self.date_to_year) or (int(self.date_from_year) == int(self.date_to_year) and int(self.date_from_month) > int(self.date_to_month)):
            raise UserError('Ngày bắt đầu không được lớn hơn ngày kết thúc!')
        
        # Tạo action để gọi report
        return self.env.ref('ccv_rp_bonus_history_report.action_report_bonus_history_xlsx').report_action(self)
