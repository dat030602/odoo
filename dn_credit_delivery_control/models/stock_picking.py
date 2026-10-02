from odoo import api, fields, models, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_credit_blocked = fields.Boolean(string='Credit Blocked', stored=True)
    block_reason = fields.Text(string='Block Reason')
    credit_released_by = fields.Many2one('res.users', string='Credit Released By')
    credit_released_date = fields.Datetime(string='Credit Released Date')

    def button_validate(self):
        for picking in self.filtered(lambda p: p.picking_type_code == 'outgoing'):
            if not picking.partner_id:
                continue
            ok, reason = picking.partner_id.commercial_partner_id._credit_check_for_delivery(picking)
            if not ok and not picking.credit_released_by:
                picking.write({
                    'is_credit_blocked': True,
                    'block_reason': reason
                })
                raise UserError(_("Delivery blocked: %s") % reason)
        return super().button_validate()

    def action_release_delivery(self):
        self.ensure_one()
        return {
            'name': _('Release Delivery'),
            'type': 'ir.actions.act_window',
            'res_model': 'credit.release.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id}
        }
