# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date

class AlphaInternalAccount(models.Model):
    _name = 'alpha.internal.account'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
    _description = 'Đề nghị tạm ứng'

    name = fields.Char(string="Tên")
    date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self), string="Ngày lên đơn")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', default=23, store=True, readonly=False)
    total_amount = fields.Monetary(string="Số tiền", readonly=False, currency_field='company_currency_id', help="Total amount impacted by the automatic entry.")

    journal_id = fields.Many2one('account.journal', string="Sổ nhật ký",
        domain="[('company_id', '=', company_id)]",
        compute="_compute_journal_id",
        inverse="_inverse_journal_id",
        help="Journal where to create the entry.", store=True, readonly=False)
    account_id = fields.Many2one(string="Từ tài khoản", comodel_name='account.account',
                                             help="Account to transfer to.")
    destination_account_id = fields.Many2one(string="Đến tài khoản", comodel_name='account.account', help="Account to transfer to.")
    employee_id = fields.Many2one("hr.employee", string="Nhân viên", compute="compute_employee_id", store=True, readonly=False)
    department_id = fields.Many2one("hr.department", string="Phòng ban", related="employee_id.department_id", store=True)
    user_id = fields.Many2one("res.users", string="Người lên đơn", default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", string="Đối tượng")
    move_id = fields.Many2one("account.move", string="Hóa đơn")
    number = fields.Integer(string="Hóa đơn", default=1)
    state = fields.Selection(
        [('draft', 'Mới'), ('approve', 'Chờ phê duyệt'), ('approved', 'Đã phê duyệt'), ('done', 'Hoàn thành'), ('cancel', 'Hủy'),], 'Trạng thái',
        default="draft",
        tracking=True, ondelete={'approve': lambda records: records.write({'state': 'draft'}), 'approve_cancel': lambda records: records.write({'state': 'draft'})})
    note = fields.Char("Nội dung")
    trp_approve_history_ids = fields.One2many('trp.approve.history', 'internal_account_id', string='Lịch sử duyệt',
                                              copy=False)

    @api.model
    def create(self, vals):
        seq_date = None
        vals['name'] = self.env['ir.sequence'].next_by_code('alpha.internal.account', sequence_date=seq_date) or 'New'
        return super(AlphaInternalAccount, self).create(vals)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.user_id = self.employee_id.user_id.id

    @api.depends("user_id")
    def compute_employee_id(self):
        for record in self:
            record.employee_id = False
            employee_id = self.env['hr.employee'].search([('user_id', '=', record.user_id.id)])
            if len(employee_id) > 0:
                record.employee_id = employee_id[0].id

    @api.depends('company_id')
    def _compute_journal_id(self):
        for record in self:
            record.journal_id = record.company_id.automatic_entry_default_journal_id

    def action_create_line(self, trp_approve_config_id):
        vals = []
        balance = self.company_currency_id._convert(self.total_amount, self.company_id.currency_id, self.company_id, fields.Date.today())
        vals.append((0, 0, {
            'name': self.note,
            'debit': balance,
            'credit': 0,
            'account_id': trp_approve_config_id.product_id.property_account_expense_id.id,
            'partner_id': self.user_id.partner_id.id,
            'amount_currency': self.total_amount,
            'currency_id': self.company_currency_id.id,
            'analytic_distribution': False,
        }))
        vals.append((0, 0, {
             'name': self.note,
             'debit': 0,
             'credit': balance,
             'account_id': trp_approve_config_id.journal_id.default_account_id.id,
             'partner_id': self.user_id.partner_id.id,
             'currency_id': self.company_currency_id.id,
             'amount_currency': - self.total_amount
        }))
        return vals
    def _inverse_journal_id(self):
        for record in self:
            record.company_id.sudo().automatic_entry_default_journal_id = record.journal_id

    def do_action(self):
        trp_approve_config_id = self.env['trp.approve.config'].search([('model_id.model', '=', 'alpha.internal.account')])
        journal_id = trp_approve_config_id.journal_id.id if not self.journal_id else self.journal_id
        move_vals = [{
            'internal_account_id': self.id,
            'currency_id': self.company_currency_id.id,
            'move_type': 'entry',
            'journal_id': journal_id.id,
            'date': date.today(),
            'ref': self.note,
            'line_ids': self.action_create_line(trp_approve_config_id)
        }]
        return self._do_action_change_account(move_vals)

    def _do_action_change_account(self, move_vals):
        new_move = self.env['account.move'].create(move_vals)
        new_move._post()
        self.write({
            'state': 'done'
        })
        return {
            'name': _("Transfer"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': new_move.id,
        }

    def action_view_invoice(self):
        return {
            'name': "Bút toán",
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('internal_account_id', '=', self.id)],
            'context': {
                'create': False,
            }
        }

    def action_cancel(self):
        if not self.trp_approve_reason_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Lý do',
                'res_model': 'trp.approve.config.reason',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_type': 'cancel',
                    'default_res_id': self.id,
                    'default_res_model': self._name,
                    'default_approve_next_action': 'action_cancel'
                },
            }
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('done', 'confirmed', 'progress'):
            self.approve_next_action = 'action_cancel'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve_cancel'
            res_approve = self.sudo().with_context(approve_type='cancel').create_approve()
        if not res_approve or not self.trp_approve_config_line_id:
            self.write({
                'state': 'cancel'
            })

    def action_undo(self):
        self.write({
            'state': 'draft'
        })

    def action_invoice_history(self):
        return {
            'name': self.name,
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'res_id': self.move_id.id,
            'context': {
                'create': False,
                'edit': False,
            }
        }

    @api.model
    def create_default_approve_config(self):
        approve_id = self.env['trp.approve.config'].search([('model_id.model', '=', self._name)])
        if not approve_id:
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            user_ids = [2]
            self.env['trp.approve.config'].create({
                'model_id': model_id.id,
                'trp_approve_config_line_ids': [
                    (0, 0, {
                        'level': 1,
                        'manager_type': 'manager',
                        'user_ids': user_ids,
                        'type': 'new',
                    }),
                    (0, 0, {
                        'level': 1,
                        'manager_type': 'manager',
                        'user_ids': user_ids,
                        'type': 'cancel',
                    })]
            })

    def action_confirm(self):
        self = self.sudo()
        if not self.employee_id.user_id:
            raise ValidationError("Nhân viên %s chưa thiết lập tài khoản người dùng" % self.employee_id.name)
        res_approve = {}
        if not self.trp_approve_config_line_id and self.state in ('draft'):
            self.approve_next_action = 'action_confirm'
            self.approve_state_init = self.state
            self.approve_state_next = 'approve'
            res_approve = self.with_context(approve_type='new').create_approve()

        if not res_approve or not self.trp_approve_config_line_id:
            if self.state == 'approve':
                trp_approve_config_id = self.env['trp.approve.config'].search([('model_id.model', '=', 'alpha.internal.account')])
                self.update({
                    'state': 'approved',
                    'account_id': trp_approve_config_id.account_id.id if (not self.journal_id and not self.journal_id.default_account_id) else self.journal_id.default_account_id.id,
                    'destination_account_id':  trp_approve_config_id.destination_account_id,
                    'journal_id': trp_approve_config_id.journal_id.id if not self.journal_id else self.journal_id
                })
                return

    is_allowed_to_complete = fields.Boolean(compute='_compute_is_allowed_to_complete')

    def _compute_is_allowed_to_complete(self):
        for rec in self:
            rec.is_allowed_to_complete = (self.env.user.login == 'tannt@ccv.vn')

    def action_force_done(self):
        from odoo.exceptions import UserError
        from odoo import _
        if self.env.user.login != 'tannt@ccv.vn':
            raise UserError(_("Bạn không có quyền thực hiện thao tác này."))
        for rec in self:
            rec.with_context(skip_approve_done=True).write({'state': 'done'})
            self.env['mail.activity'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id)]).with_context(skip_approve_done=True).unlink()
            odoobot = self.env.ref('base.partner_root', raise_if_not_found=False)
            author_id = odoobot.id if odoobot else self.env.user.partner_id.id
            rec.message_post(body=_("Phiếu đã được ép Hoàn thành (Force Done) bởi Admin."), author_id=author_id)

    def action_force_draft(self):
        from odoo.exceptions import UserError
        from odoo import _
        if self.env.user.login != 'tannt@ccv.vn':
            raise UserError(_("Bạn không có quyền thực hiện thao tác này."))
        for rec in self:
            rec.with_context(skip_approve_done=True).write({'state': 'draft', 'trp_approve_config_line_id': False})
            self.env['mail.activity'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id)]).with_context(skip_approve_done=True).unlink()
            odoobot = self.env.ref('base.partner_root', raise_if_not_found=False)
            author_id = odoobot.id if odoobot else self.env.user.partner_id.id
            rec.message_post(body=_("Phiếu đã được ép về Nháp (Force Draft) bởi Admin."), author_id=author_id)
