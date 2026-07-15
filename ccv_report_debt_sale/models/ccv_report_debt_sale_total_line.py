from odoo import api, fields, models, _

class CcvReportDebtSaleTotalLine(models.Model):
    _name = 'ccv.report.debt.sale.total.line'
    _description = 'Tổng hợp sổ tổng hợp bán hàng'
    _order = 'parent_id, team_id, user_id, partner_id'

    parent_id = fields.Many2one('ccv.report.debt.sale', string='Sổ tổng hợp bán hàng', ondelete='cascade')

    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    team_id = fields.Many2one('crm.team', string='Khu vực', related='partner_id.team_id', store=True)
    user_id = fields.Many2one('res.users', string='NV bán hàng', related='partner_id.user_id', store=True)

    price_subtotal = fields.Monetary(string='DS chưa thuế')
    price_tax = fields.Monetary(string='Thuế VAT')
    price_total = fields.Monetary(string='DS sau thuế')

    debt_old = fields.Monetary('Nợ cũ')
    debt_in = fields.Monetary('Thu nợ',)
    debt_end = fields.Monetary('Nợ cuối', compute='_compute_debt_end', store=True)

    @api.depends('debt_old', 'price_total', 'debt_in')
    def _compute_debt_end(self):
        for record in self:
            record.debt_end = record.debt_old + record.price_total - record.debt_in
    
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)

    def action_view_move(self):
        account_move_ids = self.env['account.move.line'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_id.state', '=', 'posted'),
            ('date', '>=', self.parent_id.date_from),
            ('date', '<=', self.parent_id.date_to),
            ('account_id','=', self.parent_id.account_id.id),
        ]).mapped('move_id')
        action = self.env.ref('account.action_move_journal_line').sudo().read()[0]
        if len(account_move_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = account_move_ids.id
        else:
            action['domain'] = [('id', 'in', account_move_ids.ids)]
        return action
