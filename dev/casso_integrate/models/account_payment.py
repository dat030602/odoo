from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import traceback
import re
import requests

_logger = logging.getLogger(__name__)

MIN_SIZE_SIMPLE = 4

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    casso_id = fields.Char(string='Casso ID', readonly=True, tracking=True)
    casso_reference = fields.Char(string='Reference', readonly=True, tracking=True)
    casso_description = fields.Char(string='Description', readonly=True, tracking=True)
    casso_amount = fields.Float(string='Amount', readonly=True, tracking=True)
    casso_transactionDateTime = fields.Datetime(string='Transaction Date Time', readonly=True, tracking=True)
    casso_accountNumber = fields.Char(string='Account Number', readonly=True, tracking=True)
    casso_bankName = fields.Char(string='Bank Name', readonly=True, tracking=True)
    casso_bankAbbreviation = fields.Char(string='Bank Abbreviation', readonly=True, tracking=True)
    casso_virtualAccountNumber = fields.Char(string='Virtual Account Number', readonly=True, tracking=True)
    casso_virtualAccountName = fields.Char(string='Virtual Account Name', readonly=True, tracking=True)
    casso_counterAccountName = fields.Char(string='Counterpart Account Name', readonly=True, tracking=True)
    casso_counterAccountNumber = fields.Char(string='Counterpart Account Number', readonly=True, tracking=True)
    casso_counterAccountBankId = fields.Char(string='Counterpart Account Bank ID', readonly=True, tracking=True)
    casso_counterAccountBankName = fields.Char(string='Counterpart Account Bank Name', readonly=True, tracking=True)

    def _create_casso_payment(self, data):
        try:
            _logger.info("Start _create_casso_payment with data: %s", data)
            vals = {}
            vals['casso_id'] = data.get('id', False)
            vals['casso_reference'] = data.get('reference', False)
            vals['casso_description'] = data.get('description', False)
            vals['casso_amount'] = data.get('amount', 0)
            vals['casso_transactionDateTime'] = data.get('transactionDateTime', False)
            vals['casso_accountNumber'] = data.get('accountNumber', False)
            vals['casso_bankName'] = data.get('bankName', False)
            vals['casso_bankAbbreviation'] = data.get('bankAbbreviation', False)
            vals['casso_virtualAccountNumber'] = data.get('virtualAccountNumber', False)
            vals['casso_virtualAccountName'] = data.get('virtualAccountName', False)
            vals['casso_counterAccountName'] = data.get('counterAccountName', False)
            vals['casso_counterAccountNumber'] = data.get('counterAccountNumber', False)
            vals['casso_counterAccountBankId'] = data.get('counterAccountBankId', False)
            vals['casso_counterAccountBankName'] = data.get('counterAccountBankName', False)
            is_exists = self.env['account.payment'].search([('casso_reference', '=', vals['casso_reference'])]).exists()
            if is_exists:
                return is_exists
            return self.env['account.payment'].create(vals)
        except Exception as e:
            return False

    def action_view_detail_casso_transaction(self):
        self.ensure_one()
        if not self.casso_id:
            raise UserError(_("Casso ID not found for this transaction."))
        
        config = self.env['casso.config'].search([('status', '=', 'connected')], limit=1)
        if not config:
            raise UserError(_("No connected Casso configuration found."))
        
        url = f"{config.api_url}/transactions/{self.casso_id}"
        headers = config._get_casso_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('error') != 0:
                raise UserError(_("Error from Casso API: %s", data.get('message', 'Unknown error')))
            
            transaction_data = data.get('data', {})
            if not transaction_data:
                raise UserError(_("Transaction data not found."))
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Casso Transaction Detail'),
                'res_model': 'casso.transaction.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_transaction_id': self.casso_id,
                    'default_tid': transaction_data.get('tid', ''),
                    'default_description': transaction_data.get('description', ''),
                    'default_amount': transaction_data.get('amount', 0),
                    'default_cusum_balance': transaction_data.get('cusumBalance', 0),
                    'default_when': transaction_data.get('when', False),
                    'default_bank_sub_acc_id': transaction_data.get('bankSubAccId', ''),
                },
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error when calling Casso API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                raise UserError(_("Error when getting transaction details from Casso: %s", e.response.text))
            raise UserError(_("Error when getting transaction details from Casso: %s", str(e)))
