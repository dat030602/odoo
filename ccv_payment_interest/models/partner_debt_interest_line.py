from odoo import fields, models, api

class PartnerDebtInterestLine(models.Model):
    _name = 'partner.debt.interest.line'
    _description = 'Chi tiết lãi công nợ'
    _order = 'id ASC,date'

    interest_id = fields.Many2one('partner.debt.interest', string='Tính lãi', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='interest_id.partner_id', readonly=True)
    currency_id = fields.Many2one('res.currency', related='interest_id.currency_id', readonly=True)
    rate = fields.Many2one('interest.rate.year', string='Lãi suất (%)', related='interest_id.rate')
    rate_penalty = fields.Many2one('interest.rate.year', string='Lãi phạt (%)', related='interest_id.rate_penalty')

    invoice_code = fields.Char(string='Số hóa đơn', compute='_compute_invoice', compute_sudo=True)
    move_line_id = fields.Many2one('account.move.line', string='Dòng chứng từ')
    move_id = fields.Many2one('account.move', string='Chứng từ', compute='_compute_invoice', store=True, compute_sudo=True)
    date = fields.Date(string='Ngày chứng từ', compute='_compute_invoice', store=True, compute_sudo=True)
    type = fields.Selection(string='Loại', selection=[
        ('opening','Số dư đầu kỳ'),
        ('buy','Phát sinh mua hàng'),
        ('pay','Phát sinh thanh toán/cấn trừ công nợ'),
    ])
    amount = fields.Monetary(string='Phát sinh')
    amount_buy = fields.Monetary(string='Phát sinh mua hàng', compute='_compute_amount')
    amount_pay = fields.Monetary(string='Phát sinh thanh toán/cấn trừ công nợ', compute='_compute_amount')
    balance_amount = fields.Monetary(string='Số dư')
    balance_amount_debit = fields.Monetary(string='Số dư nợ', compute='_compute_amount')
    balance_amount_credit = fields.Monetary(string='Số dư có', compute='_compute_amount')
    payment_due_date = fields.Date(string='Hạn thanh toán')
    interest_calc_date = fields.Date(string='Thời điểm tính lãi')

    delay_days = fields.Integer(string='Thời gian chậm thanh toán', compute='_compute_delay_days')
    late_interest = fields.Monetary(string='Lãi trả chậm', compute='_compute_interest')
    penalty_debt = fields.Monetary(string='Phạt quá hạn 90 ngày', compute='_compute_interest')
    total_debt = fields.Monetary(string='Tổng tiền Nợ', compute='_compute_interest')
    
    can_credit = fields.Boolean(string='Không tính lãi nợ?',related="interest_id.can_credit")

    @api.depends('amount','balance_amount')
    def _compute_amount(self):
        for rec in self:
            amount_buy = 0
            amount_pay = 0
            balance_amount_debit = 0
            balance_amount_credit = 0
            if rec.type == 'buy':
                amount_buy = abs(rec.amount)
            elif rec.type == 'pay':
                amount_pay = abs(rec.amount)
            if rec.balance_amount > 0:
                balance_amount_debit = abs(rec.balance_amount)
            else:
                balance_amount_credit = abs(rec.balance_amount)
            rec.amount_buy = amount_buy
            rec.amount_pay = amount_pay
            rec.balance_amount_debit = balance_amount_debit
            rec.balance_amount_credit = balance_amount_credit

    @api.depends('move_id')
    def _compute_invoice(self):
        for rec in self:
            if rec.move_line_id:
                rec.invoice_code = rec.move_id.vat_sinvoice_number
                rec.move_id = rec.move_line_id.move_id
                rec.date = rec.move_line_id.move_id.date
            else:
                rec.move_id = False
                rec.invoice_code = False if rec.type != 'opening' else 'Số dư đầu kỳ'
                rec.date = False

    @api.depends('payment_due_date', 'interest_calc_date','can_credit')
    def _compute_delay_days(self):
        for rec in self:
            if rec.can_credit:
                rec.delay_days = 0
            elif rec.payment_due_date and rec.interest_calc_date:
                rec.delay_days = (rec.interest_calc_date - rec.payment_due_date).days
                if rec.delay_days < 0 or rec.type != 'buy':
                    rec.delay_days = 0
            else:
                rec.delay_days = 0

    @api.depends('balance_amount', 'rate', 'delay_days')
    def _compute_interest(self):
        for rec in self:
            rate = rec.rate.rate if rec.rate else 0.0
            num_of_date = rec.rate_penalty.num_of_date if rec.rate_penalty else 0.0
            
            rate_penalty = rec.rate_penalty.rate if rec.rate_penalty else 0.0
            rec.late_interest = rec.delay_days * (rate / 36500) * rec.amount_buy if rec.delay_days > 0 else 0.0
            rec.penalty_debt = rec.amount_buy * (rate_penalty / 100) if rec.delay_days > num_of_date else 0.0
            total_debt = rec.balance_amount + rec.late_interest + rec.penalty_debt
            if total_debt > 0:
                rec.total_debt = total_debt
            else:
                rec.total_debt = 0
