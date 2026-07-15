from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    delay_days = fields.Integer(string='Thời gian chậm thanh toán', compute='_compute_delay_days')
    late_interest = fields.Monetary(string='Lãi trả chậm', compute='_compute_interest')
    penalty_debt = fields.Monetary(string='Phạt quá hạn 90 ngày', compute='_compute_interest')
    total_debt = fields.Monetary(string='Tổng tiền Nợ', compute='_compute_interest')

    @api.depends()
    def _compute_interest(self):
        for rec in self:
            delay_days = 0
            late_interest = 0
            penalty_debt = 0
            total_debt = 0
            interest_id = rec.env['partner.debt.interest'].search([('partner_id','=',rec.id)],limit=1)
            if interest_id.line_ids:
                delay_days = sum(interest_id.line_ids.mapped('delay_days'))
                balance_amount = abs(interest_id.line_ids[-1].balance_amount_debit)
                late_interest = sum(interest_id.line_ids.mapped('late_interest'))
                penalty_debt = sum(interest_id.line_ids.mapped('penalty_debt'))
                total_debt = balance_amount + late_interest + penalty_debt
            rec.delay_days = delay_days
            rec.late_interest = late_interest
            rec.penalty_debt = penalty_debt
            rec.total_debt = total_debt
