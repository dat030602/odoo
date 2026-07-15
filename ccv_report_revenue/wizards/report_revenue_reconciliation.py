from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date

class ReportRevenueReconciliationWizard(models.TransientModel):
    _name = 'report.revenue.reconciliation.wizard'
    _description = 'Bảng Kiểm kê Doanh thu'

    date_from = fields.Date(string="Từ ngày", default=date.today().strftime('%Y-%m-01'), required=True)
    date_to = fields.Date(string="Đến ngày", default=date.today(), required=True)
    partner_id = fields.Many2one('res.partner',string="Khách hàng/NCC")
    
    report_type = fields.Selection(string="Loại báo cáo", selection=[
        ('1', 'Một khách hàng'),
        ('team', 'Theo khu vực'),
        ('is_all_partner', 'Tất cả khách hàng'),
    ], default='is_all_partner')
    
    team_id = fields.Many2one("crm.team", string="Đội bán hàng", default=lambda self:self.env['crm.team'].sudo().search([
                '|', '|',
                ('user_id','=',self.sudo().env.user.id),
                ('member_ids','in',[self.sudo().env.user.id]),
                ('sales_assistant_ids','in',[self.sudo().env.user.id]),
            ], limit=1))
    
    voter_id = fields.Many2one('res.users',string="Người lập")
    chief_finance_id = fields.Many2one('res.users',string="Phòng Kế toán")
    lead_sale_id = fields.Many2one('res.users',string="Phòng Kinh doanh")
    director_id  = fields.Many2one('res.users',string="Thủ trưởng đơn vị")
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(ReportRevenueReconciliationWizard, self).default_get(fields_list)

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
    
    def action_generate_report(self):
        if self.date_from > self.date_to:
            raise UserError("Ngày bắt đầu phải nhỏ hơn ngày kết thúc.")
        return self.env.ref('ccv_report_revenue.revenue_reconciliation_report').report_action(self)
