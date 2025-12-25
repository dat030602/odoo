# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import datetime

_logger = logging.getLogger(__name__)


class SePayBankAccount(models.Model):
    _name = 'sepay.bank.account'
    _description = 'SePay Bank Account'

    parent_id = fields.Many2one('sepay.config', string='Parent Config', required=True, ondelete='cascade')
    
    account_number = fields.Char(string='Account Number', required=True)
    bank_brand_name = fields.Char(string='Bank Brand Name', readonly=True)
    bank_account_id = fields.Char(string='Bank Account ID', readonly=True)
    sub_account = fields.Char(string='Sub Account', readonly=True)
    
    # Status
    is_active = fields.Boolean(string='Active', default=True)
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    
    # Bank reference
    bank_id = fields.Many2one('vietqr.bank', string='Bank', compute='_compute_bank_id', store=True)
    
    @api.depends('bank_brand_name')
    def _compute_bank_id(self):
        """Match bank by brand name"""
        for record in self:
            if record.bank_brand_name:
                # Try to find bank by code or name
                bank = self.env['vietqr.bank'].search([
                    ('code', 'ilike', record.bank_brand_name)
                ], limit=1)
                if not bank:
                    bank = self.env['vietqr.bank'].search([
                        ('name', 'ilike', record.bank_brand_name)
                    ], limit=1)
                record.bank_id = bank.id if bank else False

    def action_sync_transactions(self, days_back=7):
        """
        Sync transactions for this specific bank account
        
        Args:
            days_back: Number of days to look back (default 7)
        """
        self.ensure_one()
        if not self.parent_id:
            raise UserError(_("Parent SePay configuration not found"))
        
        return self.parent_id.action_sync_transactions(
            account_number=self.account_number,
            days_back=days_back
        )

    def action_get_transactions(self, transaction_date_min=None, transaction_date_max=None,
                               since_id=None, limit=5000, reference_number=None,
                               amount_in=None, amount_out=None):
        """
        Get transactions for this bank account
        
        Args:
            transaction_date_min: Start date (format: YYYY-MM-DD)
            transaction_date_max: End date (format: YYYY-MM-DD)
            since_id: Get transactions from this ID onwards
            limit: Maximum number of transactions
            reference_number: Filter by reference number
            amount_in: Filter by incoming amount
            amount_out: Filter by outgoing amount
        
        Returns:
            dict: Transaction data from SePay API
        """
        self.ensure_one()
        if not self.parent_id:
            raise UserError(_("Parent SePay configuration not found"))
        
        return self.parent_id.action_get_transactions(
            account_number=self.account_number,
            transaction_date_min=transaction_date_min,
            transaction_date_max=transaction_date_max,
            since_id=since_id,
            limit=limit,
            reference_number=reference_number,
            amount_in=amount_in,
            amount_out=amount_out
        )

    def action_discover_accounts(self):
        """
        Discover bank accounts from SePay by fetching recent transactions
        and extracting unique account numbers
        """
        self.ensure_one()
        if not self.parent_id:
            raise UserError(_("Parent SePay configuration not found"))
        
        try:
            # Get recent transactions to discover accounts
            data = self.parent_id.action_get_transactions(limit=5000)
            transactions = data.get('transactions', [])
            
            # Extract unique account numbers
            account_map = {}
            for transaction in transactions:
                acc_num = transaction.get('account_number')
                if acc_num and acc_num not in account_map:
                    account_map[acc_num] = {
                        'account_number': acc_num,
                        'bank_brand_name': transaction.get('bank_brand_name'),
                        'bank_account_id': transaction.get('bank_account_id'),
                        'sub_account': transaction.get('sub_account'),
                    }
            
            # Create or update bank accounts
            created_count = 0
            for acc_num, acc_data in account_map.items():
                existing = self.search([
                    ('parent_id', '=', self.parent_id.id),
                    ('account_number', '=', acc_num)
                ], limit=1)
                
                if existing:
                    existing.write(acc_data)
                else:
                    acc_data['parent_id'] = self.parent_id.id
                    self.create(acc_data)
                    created_count += 1
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Account Discovery'),
                    'message': _('Found %d accounts, created %d new accounts') % (len(account_map), created_count),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error discovering accounts: {str(e)}")
            raise UserError(_("Error discovering accounts: %s", str(e)))

