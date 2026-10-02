from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(selection_add=[('credit_hold', 'Credit Hold')], ondelete={'credit_hold': 'set default'})
    credit_block_reason = fields.Text(string='Credit Block Reason')
    credit_exposure_snapshot = fields.Monetary(string='Credit Exposure Snapshot')
    credit_approved_by = fields.Many2one('res.users', string='Credit Approved By')
    credit_approved_date = fields.Datetime(string='Credit Approved Date')

    def action_confirm(self):
        if self.env.context.get('skip_credit_check'):
            return super().action_confirm()
            
        to_hold = self.env['sale.order']
        for order in self:
            ok, reason = order.partner_id.commercial_partner_id._credit_check(order)
            if not ok and not order._has_valid_credit_approval():
                order._put_on_hold(reason)
                to_hold |= order
        
        if to_hold:
            return super(SaleOrder, self - to_hold).action_confirm()
        return super().action_confirm()

    def _has_valid_credit_approval(self):
        return bool(self.credit_approved_by)

    def _put_on_hold(self, reason):
        for order in self:
            order.write({
                'state': 'credit_hold',
                'credit_block_reason': reason,
                'credit_exposure_snapshot': order.partner_id.commercial_partner_id.credit_exposure,
            })
            admin_user = self.env.ref('base.user_admin', False)
            if admin_user:
                order.sudo().activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_("Please review credit hold: %s") % reason,
                    user_id=admin_user.id
                )

    def _check_approver_rights(self):
        if not self.env.user.has_group('dn_credit_sale_control.group_credit_approver') and not self.env.is_admin():
            raise UserError(_("Only Credit Approvers can approve or reject credit hold."))

    def action_approve_credit(self):
        self._check_approver_rights()
        for order in self:
            self.env['credit.release.log'].sudo().create({
                'partner_id': order.partner_id.commercial_partner_id.id,
                'sale_order_id': order.id,
                'release_type': 'sale_order',
                'exposure': order.partner_id.commercial_partner_id.credit_exposure,
                'limit': order.partner_id.commercial_partner_id.credit_limit_amount,
                'overdue_days': order.partner_id.commercial_partner_id.overdue_max_days,
                'reason': 'Approved by Manager',
                'approved_by': self.env.user.id,
                'date': fields.Datetime.now(),
            })
            order.write({
                'state': 'draft',
                'credit_approved_by': self.env.user.id,
                'credit_approved_date': fields.Datetime.now()
            })
            order.with_context(skip_credit_check=True).action_confirm()
        return True

    def action_reject_credit(self):
        self._check_approver_rights()
        for order in self:
            order.write({'state': 'cancel'})
        return True
