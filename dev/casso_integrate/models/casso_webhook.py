# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import time
import urllib.parse
import datetime

_logger = logging.getLogger(__name__)

class CassoWebhook(models.Model):
    _name = 'casso.webhook'
    _description = 'Casso Webhook'

    name = fields.Char(string='Webhook Name')
    url = fields.Char(string='Webhook URL')
    config_id = fields.Many2one('casso.config', string='Casso Configuration', required=True, ondelete='cascade')
    active = fields.Boolean(string='Active', default=True)
    status = fields.Selection([('draft', 'Draft'), ('pushed', 'Pushed')], string='Status', default='draft')

    # Info Casso
    casso_id = fields.Integer(string='Casso ID')
    casso_channel = fields.Char(string='Channel')
    casso_param1 = fields.Char(string='Param 1')
    casso_param2 = fields.Char(string='Param 2')
    casso_send_only_income = fields.Boolean(string='Send Only Income', default=True)

    @api.depends('name', 'url')
    @api.depends_context('lang')
    def _compute_display_name(self):
        for record in self:
            for record in self:
                name_display = f"{record.name} - {record.get_base_url()}{record.url}" if record.url else record.name
                record.display_name = name_display

    def action_create_webhook(self):
        self.ensure_one()
        base_url = self.get_base_url()
        url = f"{self.config_id.api_url}/webhooks"
        headers = self.config_id._get_casso_headers()
        payload = {
            'income_only': True,
            "secure_token": self.config_id.secure_token,
            "webhook": base_url + self.url
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json().get('data', {})
        self.write({
            'casso_id': response_data.get('id', False),
            'casso_channel': response_data.get('channel', False),
            'casso_param1': response_data.get('param1', False),
            'casso_param2': response_data.get('param2', False),
            'casso_send_only_income': response_data.get('income_only', True),
            'status': 'pushed',
        })
        return response.json().get('data', {})

    def action_update_webhook(self):
        self.ensure_one()
        if not self.casso_id:
            raise UserError(_("Casso ID not found for this webhook."))
        base_url = self.get_base_url()
        url = f"{self.config_id.api_url}/webhooks/{self.casso_id}"
        headers = self.config_id._get_casso_headers()
        payload = {
            'income_only': self.casso_send_only_income,
            "secure_token": self.config_id.secure_token,
            "webhook": base_url + self.url
        }
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def action_delete_webhook(self):
        self.ensure_one()
        if not self.casso_id:
            raise UserError(_("Casso ID not found for this webhook."))
        url = f"{self.config_id.api_url}/webhooks/{self.casso_id}"
        headers = self.config_id._get_casso_headers()
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            self.status = 'draft'
        return response.json()

    def unlink(self):
        for record in self:
            if record.status == 'pushed':
                record.action_delete_webhook()
        return super(CassoWebhook, self).unlink()
