from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import traceback
import re
import requests
from datetime import datetime

_logger = logging.getLogger(__name__)

MIN_SIZE_SIMPLE = 4

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # SePay fields
    sepay_id = fields.Integer(string='SePay ID', readonly=True, tracking=True)
    sepay_transaction_date = fields.Datetime(string='SePay Transaction Date', readonly=True, tracking=True)
    sepay_account_number = fields.Char(string='SePay Account Number', readonly=True, tracking=True)
    sepay_code = fields.Char(string='SePay Code', readonly=True, tracking=True)
    sepay_content = fields.Text(string='SePay Content', readonly=True, tracking=True)
    sepay_transfer_type = fields.Selection([
        ('in', 'In'),
        ('out', 'Out')
    ], string='SePay Transfer Type', readonly=True, tracking=True)
    sepay_transfer_amount = fields.Float(string='SePay Transfer Amount', readonly=True, tracking=True)
    sepay_bank_account = fields.Integer(string='SePay Bank Account ID', readonly=True, tracking=True)
    sepay_bank_account_id = fields.Many2one('sepay.bank.account', string='SePay Bank Account', compute='_compute_sepay_sub_account')
    sepay_reference_code = fields.Char(string='SePay Reference Code', readonly=True, tracking=True)
    sepay_bank_brand_name = fields.Text(string='SePay Brand Name', readonly=True, tracking=True)
    sepay_config_id = fields.Many2one('sepay.config', string='SePay Configuration', readonly=True, tracking=True)

    @api.depends('sepay_bank_account')
    def _compute_sepay_sub_account(self):
        for record in self:
            account_bank = self.env['sepay.bank.account'].search([('account_id', '=', record.sepay_bank_account)], limit=1)
            record.sepay_bank_account_id = account_bank

    def prepare_sepay_payment_data(self, data, transaction_date):
        """Prepare data for SePay payment processing"""
        bank_id = self.env['sepay.bank.account'].search([('account_id', '=', data.get('sub_account', ''))], limit=1)
        amount_in = data.get('amount_in', '0')
        amount_out = data.get('amount_out', '0')
        amount = abs(float(amount_in)) if float(amount_in) > 0 else (-1 * abs(float(amount_out)))

        data = {
            'sepay_id': data.get('id', ''),
            'sepay_transaction_date': transaction_date,
            'sepay_account_number': data.get('account_number', ''),
            'sepay_code': data.get('code', ''),
            'sepay_content': data.get('transaction_content', ''),
            'sepay_transfer_type': 'in' if float(amount_in) > 0 else 'out',
            'sepay_transfer_amount': abs(amount),
            'sepay_bank_account': data.get('bank_account_id', ''),
            'sepay_reference_code': data.get('reference_number', ''),
            'sepay_bank_brand_name': data.get('bank_brand_name', ''),
            'amount': abs(amount),
            'ref': data.get('content', ''),
            'payment_type': 'inbound' if float(amount_in) > 0 else 'outbound',
            'partner_type': 'customer' if float(amount_in) > 0 else 'supplier',
        }
        if bank_id:
            data['sepay_config_id'] = bank_id.parent_id.id
        return data

    @api.model
    def _create_sepay_payment(self, data):
        try:
            transaction_id = data.get('referenceCode', '')
            existing = self.search([('sepay_id', '=', str(transaction_id))], limit=1)
            if existing:
                return existing
            
            # Parse transaction date
            transaction_date = data.get('transaction_date', False)
            if transaction_date:
                transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d %H:%M:%S')
            
            vals = {
                **self.prepare_sepay_payment_data(data, transaction_date),
            }
            
            payment = self.create(vals)
            return payment
            
        except Exception as e:
            _logger.error(f"Error in _create_sepay_payment: {str(e)}\n{traceback.format_exc()}")
            raise UserError(_("Error creating SePay payment: %s", str(e)))

    def action_view_detail_sepay_transaction(self):
        """View detailed SePay transaction information"""
        self.ensure_one()
        if not self.sepay_transaction_id:
            raise UserError(_("SePay Transaction ID not found for this transaction."))
        
        config = self.env['sepay.config'].search([('status', '=', 'connected')], limit=1)
        if not config:
            raise UserError(_("No connected SePay configuration found."))
        
        try:
            transaction_data = config.action_get_transaction_detail(self.sepay_transaction_id)
            data = self.prepare_sepay_payment_data(transaction_data)
            context = {**self.env.context}
            for key, value in data.items():
                context.update({('default_%s' % key): value})
            return {
                'type': 'ir.actions.act_window',
                'name': _('SePay Transaction Detail'),
                'res_model': 'sepay.transaction.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': context,
            }
        except Exception as e:
            _logger.error(f"Error when getting SePay transaction details: {str(e)}")
            raise UserError(_("Error when getting transaction details from SePay: %s", str(e)))
