from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountSelectionWizard(models.TransientModel):
    _name = 'account.selection.wizard'
    _description = 'Wizard for selecting debit and credit accounts'

    mass_period_id = fields.Many2one('average.price.end.period.mass', string='Mass Period')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account', required=True)

    def confirm_selection(self):
        # Create a journal entry with the selected debit and credit accounts
        if not self.mass_period_id.end_cost_allocation_ids:
            raise UserError("No end cost allocation lines found in the mass period.")

        if any(not line.cost_id.account_consolidated_ids for line in self.mass_period_id.end_cost_allocation_ids):
            raise UserError("Please select a credit account for all lines.")

        self.mass_period_id.write({
            'carryover_journal_id': self.journal_id.id,
            'carryover_debit_account_id': self.debit_account_id.id,
        })
        self.mass_period_id.auto_carryover()