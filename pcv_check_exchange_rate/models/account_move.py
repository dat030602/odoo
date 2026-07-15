from odoo import fields, models, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    tag_ids = fields.Many2many('account.move.tag')

    def action_check_manual_exchange_rate(self):
        self.ensure_one()
        purchase_ids = self.line_ids.purchase_line_id.order_id.ids
        action = self.env.ref('pcv_check_exchange_rate.action_check_exchange_rate_wizard').sudo().read()[0]
        action['context'] = {
            'default_move_id': self.id,
            'default_purchase_ids': [(6, 0, purchase_ids)]
        }
        return action

    def action_post(self):
        # OVERRIDE
        for move in self:
            if move.company_id and move.company_id.large_amount_warning_threshold:
                threshold_amount = move.company_id.threshold_amount
                for line in move.line_ids:
                    if line.debit > threshold_amount or line.credit > threshold_amount:
                        action = self.env.ref('pcv_check_exchange_rate.action_confirm_post_threshold_entries_wizard').sudo().read()[0]
                        action['context'] = {
                            'default_move_id': move.id,
                        }
                        return action
        return super().action_post()
