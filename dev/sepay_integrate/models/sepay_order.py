# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import datetime

_logger = logging.getLogger(__name__)


class SePayOrder(models.Model):
    _name = 'sepay.order'
    _description = 'SePay Order'

    name = fields.Char(string='Order Name', compute='_compute_name', store=True)
    bank_id = fields.Many2one('sepay.bank.account', string='Bank Account', required=True)
    bank_config_id = fields.Many2one('sepay.config', string='Bank Configuration', related='bank_id.parent_id', store=True)
    va_holder_name = fields.Char(string='VA Holder Name', related='bank_id.account_holder_name', store=True)
    sepay_order_id = fields.Char(string='SePay Order ID')

    # Order reference
    order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    amount = fields.Float(string='Amount')
    currency_id = fields.Many2one('res.currency', string='Currency', related='order_id.currency_id', store=True)
    qr_url = fields.Char(string='QR Code URL')
    qr_code = fields.Image(string='QR Code Data')

    # Expiration settings
    duration_type = fields.Selection([
        ('seconds', 'Seconds'),
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days')
    ], string='Duration Type', default='minutes')
    duration = fields.Integer(string='Duration', default=60)
    expiration_datetime = fields.Datetime(string='Expiration Datetime', compute='_compute_expiration_datetime', store=True)
    max_duration = fields.Integer(string='Max Duration (sec)', default=31536000, readonly=True)  # 1 year in seconds

    date_pushed = fields.Datetime(string='Date Pushed to Sepay', default=fields.Datetime.now)
    @api.constrains('duration', 'duration_type', 'max_duration')
    def _check_duration(self):
        for record in self:
            if record.duration_type == 'seconds':
                total_seconds = record.duration
            elif record.duration_type == 'minutes':
                total_seconds = record.duration * 60
            elif record.duration_type == 'hours':
                total_seconds = record.duration * 60 * 60
            elif record.duration_type == 'days':
                total_seconds = record.duration * 24 * 60 * 60
            if total_seconds > record.max_duration:
                raise UserError(_("Duration exceeds maximum allowed duration."))

    @api.depends('duration', 'date_pushed')
    def _compute_expiration_datetime(self):
        for record in self:
            if record.date_pushed and record.duration:
                if record.duration_type == 'seconds':
                    record.expiration_datetime = record.date_pushed + datetime.timedelta(seconds=record.duration)
                elif record.duration_type == 'minutes':
                    record.expiration_datetime = record.date_pushed + datetime.timedelta(minutes=record.duration)
                elif record.duration_type == 'hours':
                    record.expiration_datetime = record.date_pushed + datetime.timedelta(hours=record.duration)
                elif record.duration_type == 'days':
                    record.expiration_datetime = record.date_pushed + datetime.timedelta(days=record.duration)
            else:
                record.expiration_datetime = False
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('created', 'Created'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')

    va_ids = fields.One2many('sepay.order.va', 'parent_id', string='Virtual Accounts')

    @api.onchange('order_id')
    def _onchange_order_id(self):
        for record in self:
            if record.order_id:
                record.amount = record.order_id.amount_total

    @api.depends('bank_id', 'id')
    def _compute_name(self):
        for record in self:
            record.name = self.env['ir.sequence'].next_by_code('sepay.va.order') or "VA-Undefined"

    def _get_sepay_va_orders(self):
        self.ensure_one()
        url = f"{self.bank_id.parent_id.api_url}/bidv/{self.bank_id.account_id}/orders"
        headers = self.bank_id.parent_id._get_sepay_headers()

        headers = {
            'Authorization': f'Bearer {self.bank_id.parent_id.api_token}',
            'Content-Type': 'application/json',
        }

        payload = {}

        try:
            response = requests.get(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('orders', [])
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error creating SePay VA Order: {e}')
            raise UserError(_("Failed to create SePay VA Order. Please check the logs for details."))

    def _get_sepay_order(self):
        self.ensure_one()
        if not self.sepay_order_id:
            raise UserError(_("SePay Order ID is not set."))
        url = f"{self.bank_id.parent_id.api_url}/bidv/{self.bank_id.account_id}/orders/{self.sepay_order_id}"
        headers = self.bank_id.parent_id._get_sepay_headers()

        headers = {
            'Authorization': f'Bearer {self.bank_id.parent_id.api_token}',
            'Content-Type': 'application/json',
        }

        payload = {}

        try:
            response = requests.get(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {})
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error creating SePay VA Order: {e}')
            raise UserError(_("Failed to create SePay VA Order. Please check the logs for details."))

    def _create_sepay_order(self):
        self.ensure_one()
        url = f"{self.bank_id.parent_id.api_url}/bidv/{self.bank_id.account_id}/orders"
        headers = self._get_sepay_headers()

        headers = {
            'Authorization': f'Bearer {self.bank_id.parent_id.api_token}',
            'Content-Type': 'application/json',
        }

        payload = {
            "amount": self.amount,
            "order_code": self.name,
            "duration": self.duration,
            "with_qrcode": True
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json().get('data', {})
            self.sepay_order_id = response_data.get('order_id')
            self.status = 'created'
            self.expiration_datetime = datetime.datetime.fromisoformat(response_data.get('expiration_datetime')) - datetime.timedelta(hours=7)
            self.qr_url = response_data.get('qr_url')
            self.qr_code = response_data.get('qr_code')
            
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error creating SePay VA Order: {e}')
            raise UserError(_("Failed to create SePay VA Order. Please check the logs for details."))

    def _cancel_sepay_order(self):
        self.ensure_one()
        if not self.sepay_order_id:
            raise UserError(_("SePay Order ID is not set."))
        url = f"{self.bank_id.parent_id.api_url}/bidv/{self.bank_id.account_id}/orders/{self.sepay_order_id}"
        headers = self.bank_id.parent_id._get_sepay_headers()

        headers = {
            'Authorization': f'Bearer {self.bank_id.parent_id.api_token}',
            'Content-Type': 'application/json',
        }

        payload = {}

        try:
            response = requests.delete(url, json=payload, headers=headers)
            response.raise_for_status()
            self.status = 'cancelled'
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error cancelling SePay VA Order: {e}')
            raise UserError(_("Failed to cancel SePay VA Order. Please check the logs for details."))

    def _update_sepay_order_f_input(self, data):
        self.ensure_one()
        status = {
            'Paid': 'paid',
            'Unpaid': 'created',
            'Partial': 'partial',
        }
        self.va_holder_name = data.get('account_holder_name', '')
        self.sepay_order_id = data.get('id', '')
        self.status = status.get(data.get('status', ''), 'created')
        self.amount = data.get('amount', 0.0)
        for va_data in data.get('va', []):
            va_record = self.va_ids.filtered(lambda va: va.va_number == va_data.get('va_number'))
            if va_record:
                va_record._update_sepay_va_order_f_input(va_data)
            else:
                self.env['sepay.order.va'].create({
                    'parent_id': self.id,
                    'va_number': va_data.get('va_number', ''),
                    'va_holder_name': va_data.get('va_holder_name', ''),
                    'amount': va_data.get('amount', 0.0),
                    'status': va_data.get('status', ''),
                    'expired_at': va_data.get('expired_at', False),
                    'paid_at': va_data.get('paid_at', False),
                })