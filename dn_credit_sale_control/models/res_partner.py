from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_limit_amount = fields.Monetary(string='Credit Limit', tracking=True)
    max_overdue_days = fields.Integer(string='Max Overdue Days', default=30)
    grace_amount = fields.Monetary(string='Grace Amount')
    credit_check_enabled = fields.Boolean(string='Enable Credit Check', default=False)
    credit_exposure = fields.Monetary(compute='_compute_credit_exposure', string='Credit Exposure')
    overdue_amount = fields.Monetary(compute='_compute_overdue', string='Overdue Amount')
    overdue_max_days = fields.Integer(compute='_compute_overdue', string='Max Overdue Days Actual')

    def _compute_credit_exposure(self):
        for partner in self:
            commercial_partner = partner.commercial_partner_id
            
            # Receivable
            receivable = commercial_partner.credit
            
            # Uninvoiced SO
            uninv_so = sum(self.env['sale.order'].search([
                ('partner_id.commercial_partner_id', '=', commercial_partner.id),
                ('state', 'in', ('sale', 'done')),
                ('invoice_status', '=', 'to invoice')
            ]).mapped('amount_total'))
            
            partner.credit_exposure = receivable + uninv_so

    def _compute_overdue(self):
        for partner in self:
            commercial_partner = partner.commercial_partner_id
            invoices = self.env['account.move'].search([
                ('partner_id.commercial_partner_id', '=', commercial_partner.id),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', fields.Date.context_today(self))
            ])
            partner.overdue_amount = sum(invoices.mapped('amount_residual'))
            
            if invoices:
                oldest_date = min(invoices.mapped('invoice_date_due'))
                partner.overdue_max_days = (fields.Date.context_today(self) - oldest_date).days
            else:
                partner.overdue_max_days = 0

    def _credit_check(self, order):
        self.ensure_one()
        if not self.credit_check_enabled:
            return True, ""
            
        exposure = self.credit_exposure + order.amount_total
        if self.credit_limit_amount > 0 and (exposure - self.grace_amount) > self.credit_limit_amount:
            return False, _("Credit Limit Exceeded")
            
        if self.max_overdue_days > 0 and self.overdue_max_days > self.max_overdue_days:
            return False, _("Max Overdue Days Exceeded")
            
        return True, ""

    def _credit_check_for_delivery(self, picking):
        self.ensure_one()
        if not self.credit_check_enabled:
            return True, ""
            
        if self.max_overdue_days > 0 and self.overdue_max_days > self.max_overdue_days:
            return False, _("Max Overdue Days Exceeded for Delivery")
            
        return True, ""
