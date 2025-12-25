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
    sepay_transaction_id = fields.Char(string='SePay Transaction ID', readonly=True, tracking=True, index=True)
    sepay_reference_number = fields.Char(string='SePay Reference Number', readonly=True, tracking=True, index=True)
    sepay_code = fields.Char(string='SePay Code', readonly=True, tracking=True)
    sepay_transaction_content = fields.Text(string='SePay Transaction Content', readonly=True, tracking=True)
    sepay_amount_in = fields.Float(string='SePay Amount In', readonly=True, tracking=True)
    sepay_amount_out = fields.Float(string='SePay Amount Out', readonly=True, tracking=True)
    sepay_accumulated = fields.Float(string='SePay Accumulated Balance', readonly=True, tracking=True)
    sepay_transaction_date = fields.Datetime(string='SePay Transaction Date', readonly=True, tracking=True)
    sepay_account_number = fields.Char(string='SePay Account Number', readonly=True, tracking=True)
    sepay_bank_brand_name = fields.Char(string='SePay Bank Brand Name', readonly=True, tracking=True)
    sepay_bank_account_id = fields.Char(string='SePay Bank Account ID', readonly=True, tracking=True)
    sepay_sub_account = fields.Char(string='SePay Sub Account', readonly=True, tracking=True)

    @api.model
    def _create_sepay_payment(self, data):
        """
        Create account.payment record from SePay transaction data
        
        Args:
            data: Dictionary containing SePay transaction data
        
        Returns:
            account.payment: Created payment record
        """
        try:
            _logger.info("Start _create_sepay_payment with data: %s", data)
            
            # Check if transaction already exists
            transaction_id = data.get('id')
            if transaction_id:
                existing = self.search([('sepay_transaction_id', '=', str(transaction_id))], limit=1)
                if existing:
                    _logger.info(f"Transaction {transaction_id} already exists, updating...")
                    existing._update_sepay_payment(data)
                    return existing
            
            # Parse transaction date
            transaction_date = data.get('transaction_date')
            if transaction_date:
                try:
                    # Format: "2023-05-05 19:59:48"
                    transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d')
                    except:
                        transaction_date = False
            
            # Calculate amount (use amount_in if available, otherwise amount_out)
            amount_in = float(data.get('amount_in', 0) or 0)
            amount_out = float(data.get('amount_out', 0) or 0)
            amount = amount_in if amount_in > 0 else -amount_out
            
            vals = {
                'sepay_transaction_id': str(data.get('id', '')),
                'sepay_reference_number': data.get('reference_number'),
                'sepay_code': data.get('code'),
                'sepay_transaction_content': data.get('transaction_content', ''),
                'sepay_amount_in': amount_in,
                'sepay_amount_out': amount_out,
                'sepay_accumulated': float(data.get('accumulated', 0) or 0),
                'sepay_transaction_date': transaction_date,
                'sepay_account_number': data.get('account_number'),
                'sepay_bank_brand_name': data.get('bank_brand_name'),
                'sepay_bank_account_id': data.get('bank_account_id'),
                'sepay_sub_account': data.get('sub_account'),
                'amount': abs(amount),
                'date': transaction_date.date() if transaction_date else fields.Date.today(),
                'ref': data.get('reference_number') or data.get('transaction_content', '')[:50],
            }
            
            payment = self.create(vals)
            _logger.info(f"Created SePay payment: {payment.id} for transaction {transaction_id}")
            return payment
            
        except Exception as e:
            _logger.error(f"Error in _create_sepay_payment: {str(e)}\n{traceback.format_exc()}")
            return False

    def _update_sepay_payment(self, data):
        """
        Update existing account.payment record with SePay transaction data
        
        Args:
            data: Dictionary containing SePay transaction data
        """
        self.ensure_one()
        try:
            # Parse transaction date
            transaction_date = data.get('transaction_date')
            if transaction_date:
                try:
                    transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d')
                    except:
                        transaction_date = False
            
            amount_in = float(data.get('amount_in', 0) or 0)
            amount_out = float(data.get('amount_out', 0) or 0)
            amount = amount_in if amount_in > 0 else -amount_out
            
            self.write({
                'sepay_reference_number': data.get('reference_number') or self.sepay_reference_number,
                'sepay_code': data.get('code') or self.sepay_code,
                'sepay_transaction_content': data.get('transaction_content', '') or self.sepay_transaction_content,
                'sepay_amount_in': amount_in,
                'sepay_amount_out': amount_out,
                'sepay_accumulated': float(data.get('accumulated', 0) or 0),
                'sepay_transaction_date': transaction_date or self.sepay_transaction_date,
                'sepay_account_number': data.get('account_number') or self.sepay_account_number,
                'sepay_bank_brand_name': data.get('bank_brand_name') or self.sepay_bank_brand_name,
                'sepay_bank_account_id': data.get('bank_account_id') or self.sepay_bank_account_id,
                'sepay_sub_account': data.get('sub_account') or self.sepay_sub_account,
                'amount': abs(amount),
                'date': transaction_date.date() if transaction_date else self.date,
                'ref': data.get('reference_number') or data.get('transaction_content', '')[:50] or self.ref,
            })
            _logger.info(f"Updated SePay payment: {self.id}")
        except Exception as e:
            _logger.error(f"Error in _update_sepay_payment: {str(e)}\n{traceback.format_exc()}")

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
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('SePay Transaction Detail'),
                'res_model': 'sepay.transaction.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_transaction_id': self.sepay_transaction_id,
                    'default_account_number': transaction_data.get('account_number', ''),
                    'default_transaction_content': transaction_data.get('transaction_content', ''),
                    'default_amount_in': transaction_data.get('amount_in', 0),
                    'default_amount_out': transaction_data.get('amount_out', 0),
                    'default_accumulated': transaction_data.get('accumulated', 0),
                    'default_transaction_date': transaction_data.get('transaction_date', False),
                    'default_bank_brand_name': transaction_data.get('bank_brand_name', ''),
                    'default_reference_number': transaction_data.get('reference_number', ''),
                },
            }
        except Exception as e:
            _logger.error(f"Error when getting SePay transaction details: {str(e)}")
            raise UserError(_("Error when getting transaction details from SePay: %s", str(e)))
