# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import datetime

_logger = logging.getLogger(__name__)


class SePayOrderVA(models.Model):
    _name = 'sepay.order.va'
    _description = 'SePay Order Virtual Account'

    parent_id = fields.Many2one('sepay.order', string='SePay Order', required=True, ondelete='cascade')

    va_number = fields.Char(string='VA Number')
    va_holder_name = fields.Char(string='VA Holder Name')
    amount = fields.Float(string='Amount')
    status = fields.Char(string='Status')
    expired_at = fields.Datetime(string='Expired At')
    paid_at = fields.Datetime(string='Paid At')

    def _create_sepay_va_order(self):
        self.ensure_one()
        if not self.parent_id.sepay_order_id:
            raise UserError(_("Parent SePay Order must be created before creating VA Order."))
        url = f"{self.parent_id.bank_config_id.api_url}/bidv/{self.parent_id.bank_id.account_id}/orders/{self.parent_id.sepay_order_id}/va"
        headers = self.parent_id.bank_config_id._get_sepay_headers()
  
        headers = {
            'Authorization': f'Bearer {self.parent_id.bank_config_id.api_token}',
            'Content-Type': 'application/json',
        }

        payload = {
            "amount": self.amount,
            "duration": self.parent_id.duration,
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.va_number = data.get('data', {}).get('va_number')
            self.va_holder_name = data.get('data', {}).get('va_holder_name')
            self.status = data.get('data', {}).get('status')
            expired_at_str = data.get('data', {}).get('expired_at')
            if expired_at_str:
                self.expired_at = datetime.datetime.fromisoformat(expired_at_str) - datetime.timedelta(hours=7)
            _logger.info(f'SePay VA Order created successfully: {data}')
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error creating SePay VA Order: {e}')
            raise UserError(_("Failed to create SePay VA Order. Please check the logs for details."))

    def _cancel_sepay_va_order(self):
        self.ensure_one()
        if not self.parent_id.sepay_order_id:
            raise UserError(_("Parent SePay Order ID is not set."))
        url = f"{self.parent_id.bank_config_id.api_url}/bidv/{self.parent_id.bank_id.account_id}/orders/{self.parent_id.sepay_order_id}/va/{self.va_number}"
        headers = self.parent_id.bank_config_id._get_sepay_headers()

        headers = {
            'Authorization': f'Bearer {self.parent_id.bank_config_id.api_token}',
            'Content-Type': 'application/json',
        }
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            self.status = 'Cancelled'
            _logger.info(f'SePay VA Order cancelled successfully: {self.va_number}')
        else:
            _logger.error(f'Error cancelling SePay VA Order: {response.text}')
            raise UserError(_("Failed to cancel SePay VA Order. Please check the logs for details."))

    def _update_sepay_va_order_f_input(self, data):
        self.ensure_one()
        self.status = data.get('status')
        paid_at_str = data.get('paid_at')
        if paid_at_str:
            self.paid_at = datetime.datetime.fromisoformat(paid_at_str) - datetime.timedelta(hours=7)