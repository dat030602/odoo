from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date

class StockMoveReportWizard(models.TransientModel):
    _name = 'stock.move.report.wizard'
    _description = 'Wizard to generate Stock Move Report'

    start_date = fields.Date(string="Từ ngày", default=date.today().strftime('%Y-%m-01'), required=True)
    end_date = fields.Date(string="Đến ngày", default=date.today(), required=True)
    team_id = fields.Many2one("crm.team", string="Đội bán hàng", default=lambda self:self.env['crm.team'].sudo().search([
                '|', '|',
                ('user_id','=',self.sudo().env.user.id),
                ('member_ids','in',[self.sudo().env.user.id]),
                ('sales_assistant_ids','in',[self.sudo().env.user.id]),
            ], limit=1))

    def action_generate_report(self):
        if self.start_date > self.end_date:
            raise UserError("Ngày bắt đầu phải nhỏ hơn ngày kết thúc.")

        return self.env.ref('ccv_bao_cao.report_stock_move_xlsx').report_action(self, data={'start_date': self.start_date, 'end_date': self.end_date, 'team_id':self.team_id._origin.id if self.team_id else False})
