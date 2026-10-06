from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta

class PeriodUnlockRequest(models.Model):
    _name = 'period.unlock.request'
    _description = 'Period Unlock Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('period.unlock.request') or 'New')
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    scope = fields.Selection([
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('inventory', 'Inventory'),
        ('expense', 'Expense')
    ], required=True)
    res_model = fields.Char('Model')
    res_id = fields.Integer('Record ID')
    reason = fields.Text(required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked')
    ], default='draft', tracking=True)
    approver_id = fields.Many2one('res.users', tracking=True)
    approved_date = fields.Datetime()
    grant_start = fields.Datetime()
    grant_end = fields.Datetime()
    line_ids = fields.One2many('period.unlock.log', 'request_id')

    def action_submit(self):
        for req in self:
            req.sudo().write({'state': 'submitted'})
            manager_user = self.env.ref('dn_period_closing_control.group_period_lock_manager').user_ids[:1]
            req.sudo().activity_schedule(
                'mail.mail_activity_data_todo',
                note=_("Please review unlock request"),
                user_id=manager_user.id if manager_user else self.env.user.id
            )
        return True

    def _check_manager_rights(self):
        if not self.env.user.has_group('dn_period_closing_control.group_period_lock_manager') and not self.env.is_admin():
            raise UserError(_("Only Period Lock Managers can perform this action."))

    def action_approve(self):
        self._check_manager_rights()
        for req in self:
            req.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'grant_start': fields.Datetime.now(),
                'grant_end': fields.Datetime.now() + timedelta(hours=2)
            })
        return True

    def action_reject(self):
        self._check_manager_rights()
        self.write({'state': 'rejected'})
        return True
        
    def action_revoke(self):
        self._check_manager_rights()
        self.write({'state': 'revoked'})
        return True

    @api.model
    def _cron_expire_requests(self):
        requests = self.search([
            ('state', '=', 'approved'),
            ('grant_end', '<=', fields.Datetime.now())
        ])
        requests.write({'state': 'expired'})
        return True

class PeriodUnlockLog(models.Model):
    _name = 'period.unlock.log'
    _description = 'Period Unlock Log'

    request_id = fields.Many2one('period.unlock.request')
    res_model = fields.Char()
    res_id = fields.Integer()
    operation = fields.Selection([('create', 'Create'), ('write', 'Write'), ('unlink', 'Unlink')])
    values_before = fields.Text()
    values_after = fields.Text()
    user_id = fields.Many2one('res.users')
    date = fields.Datetime(default=fields.Datetime.now)
