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
    sepay_gateway = fields.Char(string='SePay Gateway', readonly=True, tracking=True)
    sepay_transaction_date = fields.Datetime(string='SePay Transaction Date', readonly=True, tracking=True)
    sepay_account_number = fields.Char(string='SePay Account Number', readonly=True, tracking=True)
    sepay_code = fields.Char(string='SePay Code', readonly=True, tracking=True)
    sepay_content = fields.Text(string='SePay Content', readonly=True, tracking=True)
    sepay_transfer_type = fields.Selection([
        ('in', 'In'),
        ('out', 'Out')
    ], string='SePay Transfer Type', readonly=True, tracking=True)
    sepay_transfer_amount = fields.Float(string='SePay Transfer Amount', readonly=True, tracking=True)
    sepay_sub_account = fields.Char(string='SePay Sub Account', readonly=True, tracking=True)
    sepay_reference_code = fields.Char(string='SePay Reference Code', readonly=True, tracking=True)
    sepay_description = fields.Text(string='SePay Description', readonly=True, tracking=True)

    def prepare_sepay_payment_data(self, data):
        """Prepare data for SePay payment processing"""
        self.ensure_one()
        transaction_date = data.get('transaction_date', False)
        if transaction_date:
            transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d %H:%M:%S')

        data = {
            'sepay_id': data.get('id', ''),
            'sepay_gateway': data.get('gateway', ''),
            'sepay_transaction_date': transaction_date,
            'sepay_account_number': data.get('account_number', ''),
            'sepay_code': data.get('code', ''),
            'sepay_content': data.get('content', ''),
            'sepay_transfer_type': data.get('transfer_type', ''),
            'sepay_transfer_amount': data.get('transfer_amount', 0),
            'sepay_sub_account': data.get('sub_account', ''),
            'sepay_reference_code': data.get('reference_code', ''),
            'sepay_description': data.get('description', ''),
            'amount': abs(data.get('transfer_amount', 0)),
        }
        return data

    @api.model
    def _create_sepay_payment(self, data):
        try:
            transaction_id = data.get('referenceCode', '')
            existing = self.search([('sepay_transaction_id', '=', str(transaction_id))], limit=1)
            if existing:
                return existing
            
            # Parse transaction date
            transaction_date = data.get('transaction_date', False)
            if transaction_date:
                transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d %H:%M:%S')
            
            vals = {
                **self.prepare_sepay_payment_data(data),
                'ref': data.get('content', ''),
                'payment_type': 'inbound' if data.get('transfer_type', '') == 'in' else 'outbound',
                'partner_type': 'customer' if data.get('transfer_type', '') == 'in' else 'supplier',
            }
            
            payment = self.create(vals)
            _logger.info(f"Created SePay payment: {payment.id} for transaction {transaction_id}")
            return payment
            
        except Exception as e:
            _logger.error(f"Error in _create_sepay_payment: {str(e)}\n{traceback.format_exc()}")
            return False

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
