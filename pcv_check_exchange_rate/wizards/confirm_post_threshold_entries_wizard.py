from odoo import models, fields, api, _


class ConfirmPostThresholdEntriesWizard(models.TransientModel):
    _name = 'confirm.post.threshold.entries.wizard'
    _description = 'Confirm Post Threshold Entries Wizard'

    move_id = fields.Many2one(
        'account.move', string='Bill', required=True)

    def action_confirm_post_entry(self):
        self.ensure_one()
        self.move_id.with_context(bypass_check_threshold=True)._post()
        self.move_id.write({'tag_ids': [(6, 0, self.env.ref(
            'pcv_check_exchange_rate.large_value_entry_tag').ids)]})
        if self.move_id.state == 'posted':
            payments = self.move_id._get_payment()
            if payments:
                payments.reconcile_payments()
