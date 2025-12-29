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

    def _get_transactions(self, **kwargs):
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
        if kwargs.get('account_number', False):
            params['account_number'] = kwargs.get('account_number')
        if kwargs.get('transaction_date_min', False):
            params['transaction_date_min'] = kwargs.get('transaction_date_min')
        if kwargs.get('transaction_date_max', False):
            params['transaction_date_max'] = kwargs.get('transaction_date_max')
        if kwargs.get('since_id', False):
            params['since_id'] = kwargs.get('since_id')
        if kwargs.get('limit', False):
            params['limit'] = min(kwargs.get('limit'), 5000)
        else:
            params['limit'] = 500
        if kwargs.get('reference_number', False):
            params['reference_number'] = kwargs.get('reference_number')
        if kwargs.get('amount_in', False):
            params['amount_in'] = kwargs.get('amount_in')
        if kwargs.get('amount_out', False):
            params['amount_out'] = kwargs.get('amount_out')

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 200:
                error_msg = data.get('error') or 'Unknown error'
                raise UserError(_("SePay API Error: %s", error_msg))
            
            return data.get('transactions', {})
        except requests.exceptions.RequestException as e:
            _logger.error(f"SePay API error: {str(e)}")
            raise UserError(_("Error calling SePay API: %s", str(e)))

    def _get_transaction(self, transaction_id):
        self.ensure_one()
        data = requests.get(f"{self.api_url}/transactions/details/{transaction_id}", headers=self._get_sepay_headers())
        data.raise_for_status()
        return data.json().get('transaction', {})

    def _get_bank(self, bank_id):
        """Get bank details from SePay API"""
        self.ensure_one()
        url = f"{self.api_url}/bankaccounts/details/{bank_id}"
        headers = self._get_sepay_headers()
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 200:
                error_msg = data.get('error') or 'Unknown error'
                raise UserError(_("SePay API Error: %s", error_msg))
            
            return data.get('bankaccount', {})
        except requests.exceptions.RequestException as e:
            _logger.error(f"SePay API connection error: {str(e)}")
            raise UserError(_("Error connecting to SePay API: %s", str(e)))

    def _get_banks(self, **kwargs):
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
        url = f"{self.api_url}/bankaccounts/list"
        headers = self._get_sepay_headers()
        
        params = {}
        if kwargs.get('short_name', False):
            params['short_name'] = kwargs.get('short_name')
        if kwargs.get('last_transaction_date_min', False):
            params['last_transaction_date_min'] = kwargs.get('last_transaction_date_min')
        if kwargs.get('last_transaction_date_max', False):
            params['last_transaction_date_max'] = kwargs.get('last_transaction_date_max')
        if kwargs.get('since_id', False):
            params['since_id'] = kwargs.get('since_id')
        if kwargs.get('limit', False):
            params['limit'] = min(kwargs.get('limit'), 100)
        if kwargs.get('accumulated_min', False):
            params['accumulated_min'] = kwargs.get('accumulated_min')
        if kwargs.get('accumulated_max', False):
            params['accumulated_max'] = kwargs.get('accumulated_max')

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 200:
                error_msg = data.get('error') or 'Unknown error'
                raise UserError(_("SePay API Error: %s", error_msg))
            
            return data.get('bankaccounts', [])
        except requests.exceptions.RequestException as e:
            _logger.error(f"SePay API error: {str(e)}")
            raise UserError(_("Error calling SePay API: %s", str(e)))

    def action_get_transactions(self, **kwargs):
        """Wrapper method to call _get_transactions"""
        self.status = 'connected'
        res = self._get_transactions(**kwargs)
        for tx in res:
            self.env['account.payment'].sudo()._create_sepay_payment(tx)
        return res

    def action_get_banks(self, **kwargs):
        """Wrapper method to call _get_banks"""
        res = self._get_banks(**kwargs)
        vals = []
        for bank in res:
            exsist_bank = self.bank_acc_ids.filtered(lambda b: b.account_id == bank.get('id', ''))
            if exsist_bank:
                continue
            last_transaction = bank.get('last_transaction', False)
            if last_transaction:
                last_transaction = datetime.datetime.fromisoformat(last_transaction) - datetime.timedelta(hours=7)
            created_at = bank.get('created_at', False)
            if created_at:
                created_at = datetime.datetime.fromisoformat(created_at) - datetime.timedelta(hours=7)
            vals.append({
                'parent_id': self.id,
                'account_id': bank.get('id', ''),
                'account_holder_name': bank.get('account_holder_name', ''),
                'account_number': bank.get('account_number', ''),
                'last_transaction': last_transaction,
                'label': bank.get('label', ''),
                'active': bank.get('active', '1') == '1',
                'created_at': created_at,
                'bank_short_name': bank.get('bank_short_name', ''),
                'bank_full_name': bank.get('bank_full_name', ''),
                'bank_bin': bank.get('bank_bin', ''),
                'bank_code': bank.get('bank_code', ''),
            })
        self.bank_acc_ids = [(0, 0, val) for val in vals]
        self.status = 'connected'
        return vals

    def cron_sync_sepay_transactions(self):
        """Cron job to sync SePay transactions periodically"""
        configs = self.search([('active', '=', True)])
        for config in configs:
            payment = self.env['account.payment'].sudo().search([('sepay_config_id', '=', config.id)], order='sepay_id desc', limit=1)
            config.action_get_transactions(since_id=payment.sepay_id if payment else None)
