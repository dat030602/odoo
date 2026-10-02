from odoo import api, fields, models

class CreditReleaseWizard(models.TransientModel):
    _name = 'credit.release.wizard'
    _description = 'Credit Release Wizard'

    picking_id = fields.Many2one('stock.picking', required=True)
    reason = fields.Text(string='Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.picking_id.write({
            'is_credit_blocked': False,
            'credit_released_by': self.env.user.id,
            'credit_released_date': fields.Datetime.now()
        })
        self.env['credit.release.log'].create({
            'partner_id': self.picking_id.partner_id.commercial_partner_id.id,
            'picking_id': self.picking_id.id,
            'release_type': 'delivery',
            'exposure': self.picking_id.partner_id.commercial_partner_id.credit_exposure,
            'limit': self.picking_id.partner_id.commercial_partner_id.credit_limit_amount,
            'overdue_days': self.picking_id.partner_id.commercial_partner_id.overdue_max_days,
            'reason': self.reason,
            'approved_by': self.env.user.id,
            'date': fields.Datetime.now(),
        })
        return {'type': 'ir.actions.act_window_close'}
