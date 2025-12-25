# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import time
import urllib.parse
import datetime

_logger = logging.getLogger(__name__)

class CassoBankAccount(models.Model):
    _name = 'casso.bank.account'
    _description = 'Casso Bank Account'

    parent_id = fields.Many2one('casso.config', string='Parent Config')

    bank_id = fields.Char(string='Bank ID')
    bank_bin = fields.Char(string='Bank BIN')
    bank_code_name = fields.Char(string='Bank Code Name')
    bank_account_name = fields.Char(string='Bank Account Name')
    bank_sub_acc_id = fields.Char(string='Bank Sub Account ID')
    connect_status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], string='Connect Status')
    plan_status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], string='Plan Status')

    bank_id = fields.Many2one('vietqr.bank', string='Bank', compute='_compute_bank_id', store=True)
    @api.depends('bank_bin')
    def _compute_bank_id(self):
        for record in self:
            record.bank_id = self.env['vietqr.bank'].search([('bin', '=', record.bank_bin)], limit=1)

    def action_sync_transaction(self, date=None):
        """
        Get transaction list from Casso API
        According to documentation: https://developer.casso.vn/english-v2-new/casso-api/api/lay-giao-dich
        
        Args:
            from_date: Start date (format: YYYY-MM-DD or timestamp)
            to_date: End date (format: YYYY-MM-DD or timestamp)
            bank_sub_acc_id: Bank sub account ID to filter
            page: Page number (default: 1)
            page_size: Number of records per page (default: 20)
        
        Returns:
            dict: JSON data from Casso API
        """
        self.ensure_one()
        url = f"{self.parent_id.api_url}/transactions"
        headers = self.parent_id._get_casso_headers()
        if date:
            from_date = date.strftime('%Y-%m-%d')
        else:
            from_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        page = 1
        page_size = 20
        
        while True:
            data = []
            params = {
                'fromDate': from_date,
                'bankSubAccId': self.bank_sub_acc_id,
                'page': page,
                'pageSize': page_size,
                'sort': 'desc',
            }
            
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                data = data.get('data', [])
                totalPages = data.get('totalPages', 1)
                records = data.get('records', [])
                # TODO: Create account.payment records from records
                if page >= totalPages:
                    break
                page = data.get('nextPage', page + 1)
            except requests.exceptions.RequestException as e:
                break

