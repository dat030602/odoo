# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import datetime
import urllib.parse

_logger = logging.getLogger(__name__)


class SePayConfig(models.Model):
    _name = 'sepay.config'
    _description = 'SePay Configuration'

    name = fields.Char(string='Configuration Name', default='SePay Integration', required=True)
    api_token = fields.Char(string='API Token', required=True, help='API Token from my.sepay.vn -> API Access')
    api_url = fields.Char(string='API URL', default='https://my.sepay.vn/userapi', required=True)
    webhook_url = fields.Char(string='Webhook URL', default='/webhook/sepay', 
                              help="Example: /webhook/sepay")
    status = fields.Selection([('draft', 'Draft'), ('connected', 'Connected')], 
                             string='Status', default='draft')
    active = fields.Boolean(string='Active', default=True)
    
    # User Info
    user_email = fields.Char(string='User Email', readonly=True)
    user_name = fields.Char(string='User Name', readonly=True)
    
    # Bank Accounts
    bank_acc_ids = fields.One2many('sepay.bank.account', 'parent_id', string='Bank Accounts')

    def _get_sepay_headers(self):
        """Create headers for SePay API requests"""
        self.ensure_one()
        if not self.api_token:
            raise UserError(_("API Token is required. Please configure it in SePay settings."))
        
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

    def action_test_connection(self):
        """Test connection to SePay API"""
        self.ensure_one()
        try:
            url = f"{self.api_url}/transactions/list"
            headers = self._get_sepay_headers()
            params = {'limit': 1}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 200 and data.get('messages', {}).get('success'):
                self.write({'status': 'connected'})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection to SePay API successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = data.get('error') or data.get('messages', {}).get('error', 'Unknown error')
                raise UserError(_("SePay API Error: %s", error_msg))
        except requests.exceptions.RequestException as e:
            _logger.error(f"SePay API connection error: {str(e)}")
            raise UserError(_("Error connecting to SePay API: %s", str(e)))

    def action_get_transactions(self, account_number=None, transaction_date_min=None, 
                                transaction_date_max=None, since_id=None, limit=5000,
                                reference_number=None, amount_in=None, amount_out=None):
        """
        Get transaction list from SePay API
        According to documentation: https://sepay.vn/blog/api-mbbank-api-ngan-hang-mbbank-moi-nhat/
        
        Args:
            account_number: Filter by account number
            transaction_date_min: Start date (format: YYYY-MM-DD)
            transaction_date_max: End date (format: YYYY-MM-DD)
            since_id: Get transactions from this ID onwards (>=)
            limit: Maximum number of transactions (max 5000, default 5000)
            reference_number: Filter by reference number
            amount_in: Filter by incoming amount
            amount_out: Filter by outgoing amount
        
        Returns:
            dict: JSON data from SePay API
        """
        self.ensure_one()
        url = f"{self.api_url}/transactions/list"
        headers = self._get_sepay_headers()
        
        params = {}
        if account_number:
            params['account_number'] = account_number
        if transaction_date_min:
            params['transaction_date_min'] = transaction_date_min
        if transaction_date_max:
            params['transaction_date_max'] = transaction_date_max
        if since_id:
            params['since_id'] = since_id
        if limit:
            params['limit'] = min(limit, 5000)  # Max 5000
        if reference_number:
            params['reference_number'] = reference_number
        if amount_in:
            params['amount_in'] = amount_in
        if amount_out:
            params['amount_out'] = amount_out
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 200:
                error_msg = data.get('error') or 'Unknown error'
                raise UserError(_("SePay API Error: %s", error_msg))
            
            return data
        except requests.exceptions.RequestException as e:
            _logger.error(f"SePay API error: {str(e)}")
            raise UserError(_("Error calling SePay API: %s", str(e)))

    def action_sync_transactions(self, account_number=None, days_back=7):
        """
        Sync transactions from SePay API
        
        Args:
            account_number: Specific account number to sync (None for all)
            days_back: Number of days to look back (default 7)
        """
        self.ensure_one()
        transaction_date_min = (datetime.datetime.now() - datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        # Get transactions
        data = self.action_get_transactions(
            account_number=account_number,
            transaction_date_min=transaction_date_min,
            limit=5000
        )
        
        transactions = data.get('transactions', [])
        payment_model = self.env['account.payment'].sudo()
        created_count = 0
        updated_count = 0
        
        for transaction in transactions:
            try:
                # Check if transaction already exists
                existing = payment_model.search([
                    ('sepay_transaction_id', '=', transaction.get('id'))
                ], limit=1)
                
                if existing:
                    # Update existing transaction
                    existing._update_sepay_payment(transaction)
                    updated_count += 1
                else:
                    # Create new transaction
                    payment_model._create_sepay_payment(transaction)
                    created_count += 1
            except Exception as e:
                _logger.error(f"Error processing SePay transaction {transaction.get('id')}: {str(e)}")
                continue
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': _('Created: %d, Updated: %d transactions') % (created_count, updated_count),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_get_transaction_detail(self, transaction_id):
        """
        Get detailed information about a specific transaction
        
        Args:
            transaction_id: SePay transaction ID
        
        Returns:
            dict: Transaction details
        """
        self.ensure_one()
        # SePay API doesn't have a direct endpoint for single transaction
        # So we search by ID in the list
        data = self.action_get_transactions(since_id=transaction_id, limit=1)
        
        transactions = data.get('transactions', [])
        for transaction in transactions:
            if str(transaction.get('id')) == str(transaction_id):
                return transaction
        
        raise UserError(_("Transaction with ID %s not found") % transaction_id)

    def action_create_webhook(self):
        """
        Note: SePay webhook configuration is done on my.sepay.vn
        This method provides instructions
        """
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        webhook_full_url = base_url + self.webhook_url
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Webhook Configuration'),
                'message': _('Configure webhook at my.sepay.vn with URL: %s') % webhook_full_url,
                'type': 'info',
                'sticky': True,
            }
        }

