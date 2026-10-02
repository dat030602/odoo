from odoo import api, fields, models, _

class PeriodLock(models.Model):
    _name = 'period.lock'
    _description = 'Period Lock'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many('period.lock.line', 'lock_id', string='Lines')

class PeriodLockLine(models.Model):
    _name = 'period.lock.line'
    _description = 'Period Lock Line'

    lock_id = fields.Many2one('period.lock', required=True, ondelete='cascade')
    scope = fields.Selection([
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('inventory', 'Inventory'),
        ('expense', 'Expense')
    ], required=True)
    lock_date = fields.Date(required=True)
    applies_to_admin = fields.Boolean(default=True)
