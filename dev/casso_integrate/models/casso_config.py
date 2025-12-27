# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import time
import urllib.parse
import datetime

_logger = logging.getLogger(__name__)

class CassoConfig(models.Model):
    _name = 'casso.config'
    _description = 'Casso Config'

    name = fields.Char(string='Configuration Name', default='Casso Integration', required=True)
    client_id = fields.Char(string='Client ID', copy=False)
    client_secret = fields.Char(string='Client Secret', copy=False)
    redirect_authorize_uri = fields.Char(string='Redirect Authorize URI', default='/webhook/casso/authorize',)
    webhook_url = fields.Char(string='Webhook URL', default='/webhook/casso',)
    webhook_id = fields.Many2one('casso.webhook', string='Webhook', readonly=True)
    api_url = fields.Char(string='API URL', default='https://oauth.casso.vn/v2')
    oauth_url = fields.Char(string='OAuth URL', default='https://oauth.casso.vn')
    secure_token = fields.Char(string='Secure Token', copy=False)

    # Token Storage
    token_type = fields.Selection([('Bearer', 'OAuth2'), ('Apikey', 'API Key')], string='Token Type', default='Bearer')
    api_key = fields.Char(string='API Key', copy=False)
    access_token = fields.Char(string='Access Token', copy=False)
    refresh_token = fields.Char(string='Refresh Token', copy=False)
    token_expires_at = fields.Datetime(string='Token Expires At', copy=False)
    status = fields.Selection([('draft', 'Draft'), ('connected', 'Connected')], string='Status', default='draft', copy=False)

    # User Info
    user_user_id = fields.Char(string='User ID', copy=False)
    user_user_email = fields.Char(string='User Email', copy=False)
    user_business_id = fields.Char(string='Bussiness ID', copy=False)
    user_business_name = fields.Char(string='Business Name', copy=False)
    bank_acc_ids = fields.One2many('casso.bank.account', 'parent_id', string='Bank Accounts', copy=False)

    active = fields.Boolean(string='Active', default=True)

    def _get_casso_headers(self):
        """Use OAuth2 Token to create Header for API queries"""
        self.ensure_one()
        if self.token_type == 'Bearer':
            token = self._get_valid_token()
            return {
                'Authorization': f'{self.token_type} {token}',
                'Content-Type': 'application/json'
            }
        else:
            return {
                'Authorization': f'{self.token_type} {self.api_key}',
                'Content-Type': 'application/json'
            }

    def _get_valid_token(self):
        """Check and automatically refresh token if expired"""
        self.ensure_one()
        current_time = datetime.datetime.now()
        # If token is about to expire in the next 5 minutes, perform refresh
        if not self.access_token or (self.token_expires_at and current_time > (self.token_expires_at - datetime.timedelta(minutes=5))):
            self.action_refresh_token()
        return self.access_token

    def action_authorize_token(self):
        """
        Get OAuth2 token for the first time from Authorization Code
        Call this function when you receive code from Redirect URI
        """
        self.ensure_one()
        base_url = self.get_base_url()
        url = f"{self.oauth_url}/auth/authorize" \
            f"?client_id={urllib.parse.quote(self.client_id)}" \
            f"&scope=webhook" \
            f"&redirect_uri={urllib.parse.quote(base_url + self.redirect_authorize_uri)}" \
            f"&response_type=code"
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url,
        }

    def action_refresh_token(self):
        """
        Refresh OAuth2 token using Refresh Token
        """
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(_("Refresh Token not found. Please login again."))

        url = f"{self.oauth_url}/auth/token"
        base_url = self.get_base_url()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {urllib.parse.quote(self.client_id+":"+self.client_secret)}'
        }
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': base_url + self.redirect_authorize_uri
        }
        response = requests.post(
            url,
            json=payload,
            headers=headers
        )
        response_data = response.json()
        self.write({
            'access_token': response_data.get('access_token', ''),
            'refresh_token': response_data.get('refresh_token', ''),
            'token_expires_at': datetime.datetime.now() + datetime.timedelta(seconds=response_data.get('expires_in', 0))
        })
        return True

    def action_create_webhook(self):
        self.ensure_one()
        webhook = self.env['casso.webhook'].search([('config_id', '=', self.id), ('url', '=', self.webhook_url)], limit=1)
        if not webhook:
            webhook = self.env['casso.webhook'].create({
                'config_id': self.id,
                'url': self.webhook_url,
                'name': 'Casso Webhook'
            })
            self.webhook_id = webhook.id
            webhook.action_create_webhook()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Webhook has been created successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            if not self.webhook_id or self.webhook_id.id != webhook.id:
                self.webhook_id = webhook.id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Info'),
                    'message': _('Webhook already exists.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        

    def action_get_info_user(self):
        """
        Get user information from Casso
        """
        self.ensure_one()
        url = f"{self.api_url}/userInfo"
        headers = self._get_casso_headers()
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_data = response.json().get('data', {})
        self.write({
            'user_user_id': response_data.get('user', {}).get('id', False),
            'user_user_email': response_data.get('user', {}).get('email', False),
            'user_business_id': response_data.get('business', {}).get('id', False),
            'user_business_name': response_data.get('business', {}).get('name', False)
        })
        bank_acc_ids = response_data.get('bankAccs', [])
        for bank_acc_id in bank_acc_ids:
            bank_acc_id = bank_acc_id.get('id', False)

            bank_acc_bank = bank_acc_id.get('bank', {})
            bank_acc_bank_bin = bank_acc_bank.get('bin', False)
            bank_acc_bank_code_name = bank_acc_bank.get('codeName', False)
            
            bank_acc_bank_account_name = bank_acc_id.get('bankAccountName', False)
            bank_acc_bank_sub_acc_id = bank_acc_id.get('bankSubAccId', False)
            bank_acc_connect_status = bank_acc_id.get('connectStatus', False)
            bank_acc_plan_status = bank_acc_id.get('planStatus', False)

            bank_id = self.bank_acc_ids.filtered(lambda x: x.bank_id == bank_acc_id)

            if not bank_id:
                self.env['casso.bank.account'].create({
                    'parent_id': self.id,
                    'bank_bin': bank_acc_bank_bin,
                    'bank_code_name': bank_acc_bank_code_name,
                    'bank_account_name': bank_acc_bank_account_name,
                    'bank_sub_acc_id': bank_acc_bank_sub_acc_id,
                    'connect_status': bank_acc_connect_status,
                    'plan_status': bank_acc_plan_status
                })
            else:
                bank_id.write({
                    'bank_code_name': bank_acc_bank_code_name,
                    'bank_bin': bank_acc_bank_bin,
                    'bank_account_name': bank_acc_bank_account_name,
                    'bank_sub_acc_id': bank_acc_bank_sub_acc_id,
                    'connect_status': bank_acc_connect_status,
                    'plan_status': bank_acc_plan_status
                })
        self.write({'status': 'connected'})
        return response.json()

    def action_sync_new_transaction(self):
        self.ensure_one()
        url = f"{self.api_url}/sync"
        headers = self._get_casso_headers()
        now = datetime.datetime.now()
        for bank_acc_id in self.bank_acc_ids:
            if now - (bank_acc_id.last_sync or now) < datetime.timedelta(minutes=bank_acc_id.min_sync_interval):
                continue
            body = {
                'bank_acc_id': bank_acc_id.bank_id,
            }
            response = requests.post(url, headers=headers, json=body)
            if response.status_code != 200:
                _logger.error(f"Error when syncing transaction from Casso: {response.text}")
            bank_acc_id.last_sync = now
        return True
