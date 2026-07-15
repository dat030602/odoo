from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta, date
import json
import logging

_logger = logging.getLogger(__name__)

class PartnerDebtInterest(models.Model):
    _name = 'partner.debt.interest'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Lãi trả chậm từ công nợ'
    _order = 'partner_id,currency_id,property_payment_term_id,date_from'

    name = fields.Char(string='Tên lãi chậm', required=True)
    partner_id = fields.Many2one('res.partner', string='Đối tác', required=True)
    date_from = fields.Date(string='Từ ngày', required=True)
    date_to = fields.Date(string='Đến ngày', default=fields.Date.context_today)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    property_payment_term_id = fields.Many2one('account.payment.term', string='Lãi suất (%)', related="partner_id.property_payment_term_id")
    rate = fields.Many2one('interest.rate.year', string='Lãi suất (%)', domain="[('type','=','1')]")
    rate_penalty = fields.Many2one('interest.rate.year', string='Lãi phạt (%)', domain="[('type','=','2')]")
    line_ids = fields.One2many('partner.debt.interest.line','interest_id')

    delay_days = fields.Integer(string='Thời gian chậm thanh toán', compute='_compute_interest')
    late_interest = fields.Monetary(string='Lãi trả chậm', compute='_compute_interest')
    penalty_debt = fields.Monetary(string='Phạt quá hạn 90 ngày', compute='_compute_interest')
    total_debt = fields.Monetary(string='Tổng tiền Nợ', compute='_compute_interest')
    
    can_credit = fields.Boolean(string='Không tính lãi nợ?')
    amount_paid = fields.Monetary(string='Tổng tiền Nợ đã cấn trừ')

    @api.model
    def _cron_create_debt_interest_activity(self):
        """Cron chạy mỗi ngày, kiểm tra và tạo mail.activity cho các bản ghi có nợ."""
        # Lấy danh sách user từ ir.config_parameter
        # param_value = self.env['ir.config_parameter'].sudo().get_param('partner_debt_interest_notify_user_ids')
        # try:
        #     user_ids = json.loads(param_value or "[]")
        # except json.JSONDecodeError:
        #     user_ids = []

        # Lọc các bản ghi có tổng nợ > 0
        interest_records = self.search([])
        for interest_record in interest_records:
            interest_record.action_confirm()
        # interest_records = interest_records.filtered(lambda l:l.total_debt > 0)

        # for record in interest_records:
        #     for user_id in user_ids:
        #         # Kiểm tra nếu activity đã tồn tại, tránh tạo trùng
        #         existing = self.env['mail.activity'].search([
        #             ('res_model', '=', record._name),
        #             ('res_id', '=', record.id),
        #             ('user_id', '=', user_id),
        #             ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
        #             ('summary', '=', 'Lãi chậm thanh toán'),
        #         ], limit=1)

        #         if not existing:
        #             self.env['mail.activity'].create({
        #                 'res_model': record._name,
        #                 'res_id': record.id,
        #                 'user_id': user_id,
        #                 'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
        #                 'summary': 'Lãi chậm thanh toán',
        #                 'note': 'Khách hàng {} có tổng nợ chậm là {:.2f}. Vui lòng kiểm tra.'.format(
        #                     record.partner_id.name, record.total_debt),
        #                 'date_deadline': fields.Date.context_today(self),
        #             })

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self.sudo():
            if rec.partner_id:
                rec.name = rec.partner_id.name

    @api.depends('line_ids.balance_amount', 'line_ids.rate', 'line_ids.delay_days')
    def _compute_interest(self):
        for rec in self:
            delay_days = 0
            late_interest = 0
            penalty_debt = 0
            total_debt = 0
            if rec.line_ids:
                delay_days = sum(rec.line_ids.mapped('delay_days'))
                balance_amount = abs(rec.line_ids[-1].balance_amount_debit)
                late_interest = sum(rec.line_ids.mapped('late_interest'))
                penalty_debt = sum(rec.line_ids.mapped('penalty_debt'))
                total_debt = (balance_amount + late_interest + penalty_debt - rec.amount_paid) if balance_amount else 0
            rec.delay_days = delay_days
            rec.late_interest = late_interest
            rec.penalty_debt = penalty_debt
            rec.total_debt = total_debt

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            domain = ['|', '|', '|',
                ('partner_id.name', operator, name),
                ('partner_id.code_contact', operator, name),
                ('date_from', operator, name),
                ('date_to', operator, name),
            ]
            args = args + domain
        return self.search(args, limit=limit).name_get()

    def name_get(self):
        result = []
        for rec in self.sudo():
            partner_code = rec.partner_id.code_contact or ''
            partner_name = rec.partner_id.name or ''
            start_date = rec.date_from.strftime('%d/%m/%Y') if rec.date_from else ''
            end_date = rec.date_to.strftime('%d/%m/%Y') if rec.date_to else ''

            # Tính số ngày được nợ
            if rec.partner_id.property_payment_term_id:
                days = rec.partner_id.property_payment_term_id.line_ids.mapped('days')
                credit_days = max(days) if days else 0
            else:
                credit_days = 0
            name = "[%s] %s - được nợ %s ngày - %s - %s" % (
                partner_code,
                partner_name,
                credit_days,
                start_date,
                end_date
            )
            result.append((rec.id, name))
        return result

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        current_year = str(datetime.today().year)
        rate_rec = self.env['interest.rate.year'].search([('year', '=', current_year)])
        rate = rate_rec.filtered(lambda l: l.type == '1')
        rate_penalty = rate_rec.filtered(lambda l: l.type == '2')
        if rate:
            res['rate'] = rate[0].id
        if rate_penalty:
            res['rate_penalty'] = rate_penalty[0].id
        return res

    def action_confirm(self):
        self._get_data()

    def _get_data(self):
        """ Tính công nợ và tạo dòng interest """
        for rec in self:
            aml_obj = rec.env['account.move.line'].sudo()
            if rec.line_ids:
                rec.line_ids.unlink()

            # 1️⃣ TÍNH SỐ DƯ ĐẦU KỲ
            opening_domain = [
                ('partner_id', '=', rec.partner_id.id),
                ('parent_state', '=', 'posted'),
                ('company_id', '=', rec.env.company.id),
                ('account_id.account_type', 'in', ['asset_receivable']),
                ('date', '<', rec.date_from)
            ]
            opening_lines = aml_obj.search(opening_domain)
            opening_balance_debit = sum(opening_lines.mapped('debit'))
            opening_balance_credit = sum(opening_lines.mapped('credit'))
            opening_balance = opening_balance_debit - opening_balance_credit

            # if opening_balance != 0:
            rec.env['partner.debt.interest.line'].create({
                'interest_id': rec.id,
                'move_id': False,
                'type': 'opening',
                'amount': 0,
                'balance_amount': opening_balance,
            })

            # 2️⃣ LẤY DÒNG MOVE LINE TRONG KHOẢNG THỜI GIAN
            domain = [
                ('partner_id', '=', rec.partner_id.id),
                ('parent_state', '=', 'posted'),
                ('company_id', '=', rec.env.company.id),
                # ('reconciled', '=', False),
                ('account_id.account_type', 'in', ['asset_receivable']),
                ('move_id.date', '>=', rec.date_from),
                ('move_id.date', '<=', rec.date_to)
            ]

            move_lines = aml_obj.search(domain, order='date ASC')

            for line in move_lines:
                move_type = 'buy' if line.move_id.move_type in ['out_invoice', 'in_invoice'] else 'pay'
                move_id = line.move_id
                if line.reconciled:
                    if move_id.invoice_payments_widget:
                        invoice_payments_widget = move_id.invoice_payments_widget.get('content', False)
                        if invoice_payments_widget:
                            payment_dates = [
                                fields.Date.from_string(line.get('date'))
                                for line in invoice_payments_widget if line.get('date') and line.get('is_exchange', False)
                            ]
                            interest_calc_date = max(payment_dates) if payment_dates else move_id.date
                        else:
                            interest_calc_date = move_id.date
                    else:
                        interest_calc_date = move_id.date
                else:
                    interest_calc_date = date.today()


                if rec.partner_id.property_payment_term_id:
                    payment_term_days = rec.partner_id.property_payment_term_id.line_ids.mapped('days')
                    max_days = max(payment_term_days) if payment_term_days else 0
                    payment_due_date = line.move_id.date + timedelta(days=max_days)
                else:
                    payment_due_date = line.move_id.date
                amount = line.credit or line.debit
                opening_balance += abs(amount) if move_type == 'buy' else -abs(amount)

                rec.env['partner.debt.interest.line'].create({
                    'interest_id': rec.id,
                    'move_line_id': line.id,
                    'type': move_type,
                    'amount': amount,
                    'balance_amount': opening_balance,
                    'payment_due_date': payment_due_date,
                    'interest_calc_date': interest_calc_date,
                })

    def action_view_tree(self):
        self.ensure_one()
        lines = self.line_ids.ids
        action = self.env['ir.actions.act_window']._for_xml_id('ccv_payment_interest.partner_debt_interest_line_action')
        action['domain'] = [('id','in',lines)]
        action['context'] = {'default_interest_id': self.id}
        return action
