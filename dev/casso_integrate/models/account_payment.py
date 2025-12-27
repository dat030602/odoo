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
        vals = self._prepare_casso_json(data)
        is_exists = self.env['account.payment'].search([('casso_reference', '=', vals['casso_reference'])]).exists()
        if is_exists:
            return is_exists
        if data.get('amount', 0) < 0:
            vals.update({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
            })
        else:
            vals.update({
                'payment_type': 'inbound',
                'partner_type': 'customer',
            })
        vals.update({'amount': abs(vals.get('casso_amount', 0))})
        payment = self.env['account.payment'].create(vals)
        if payment.casso_counterAccountNumber:
            payment._match_casso_partner_by_account_number(payment.casso_counterAccountNumber)
        if payment.casso_accountNumber:
            payment._match_casso_journal_by_account_id(payment.casso_accountNumber)
        return payment

    def _match_casso_partner_by_account_number(self, account_number):
        self.ensure_one()
        partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', account_number)], limit=1)
        if partner_bank and partner_bank.partner_id:
            self.partner_id = partner_bank.partner_id

    def _match_casso_journal_by_account_id(self, account_id):
        self.ensure_one()
        bank_account_id = self.env['casso.bank.account'].search([('bank_sub_acc_id', '=', account_id)], limit=1)
        if bank_account_id and bank_account_id.journal_id:
            self.journal_id = bank_account_id.journal_id

    def _prepare_casso_json(self, data):
        return {
            'casso_id': data.get('id', False),
            'casso_reference': data.get('tid', False),
            'casso_description': data.get('description', False),
            'casso_amount': abs(data.get('amount', 0)),
            'casso_transactionDateTime': data.get('when', False),
            'casso_accountNumber': data.get('subAccId', False),
            'casso_bankName': data.get('bankName', False),
            'casso_bankAbbreviation': data.get('bankAbbreviation', False),
            'casso_virtualAccountNumber': data.get('virtualAccount', False),
            'casso_virtualAccountName': data.get('virtualAccountName', False),
            'casso_counterAccountName': data.get('corresponsiveName', False),
            'casso_counterAccountNumber': data.get('corresponsiveAccount', False),
            'casso_counterAccountBankId': data.get('corresponsiveBankId', False),
            'casso_counterAccountBankName': data.get('corresponsiveBankName', False)
        }

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

            transaction_data = {}

            for key, value in data.get('data', {}).items():
                transaction_data['default_%s' % key] = value

            return {
                'type': 'ir.actions.act_window',
                'name': _('Casso Transaction Detail'),
                'res_model': 'casso.transaction.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    **self.env.context,
                    **transaction_data,
                },
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error when calling Casso API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                raise UserError(_("Error when getting transaction details from Casso: %s", e.response.text))
            raise UserError(_("Error when getting transaction details from Casso: %s", str(e)))
