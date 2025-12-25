from odoo import models, fields, api, _
import logging
import traceback
import re

_logger = logging.getLogger(__name__)

MIN_SIZE_SIMPLE = 4

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    transaction_code = fields.Char(string='Transaction Code', readonly=True, tracking=True)
    acc_counterpart_no = fields.Char(string='Counterpart Account Number', readonly=True, tracking=True)
    acc_counterpart_name = fields.Char(string='Counterpart Account Name', readonly=True, tracking=True)
    ref_src = fields.Char(string='Reference Source', readonly=True, tracking=True)

    @api.onchange('acc_counterpart_no')
    def _onchange_acc_counterpart_no(self):
        if self.acc_counterpart_no:
            self.partner_bank_id = self.env['res.partner.bank'].search([('acc_number', '=', self.acc_counterpart_no)], limit=1)

    def action_create_payment_from_automation_bank(self, journal_id, data=[]):
        result = []
        try:
            _logger.info("Start action_create_payment_from_automation_bank with journal_id: %s, data count: %s", journal_id, len(data))
            for line in data:
                ref = line.get('ref')
                accounting_date = line.get('accounting_date')
                transaction_date = line.get('transaction_date')
                credit = line.get('credit')
                debit = line.get('debit')
                transaction_number = line.get('transaction_number')
                counterpart_account = line.get('counterpart_account')
                counterpart_name = line.get('counterpart_name')
                partner_bank_id = self.env['res.partner.bank'].search([('acc_number', '=', counterpart_account)], limit=1)
                invoice_ids = self.env['account.move']
                
                if self._check_transaction_exists(transaction_number=transaction_number):
                    _logger.info("Transaction %s already exists. Skipping.", transaction_number)
                    continue
                    
                text_list = re.sub(r'[^a-zA-Z0-9]+', ' ', ref).split() if ref else []
                text_list = [text for text in text_list if len(text) >= MIN_SIZE_SIMPLE]
                _logger.debug("Searching invoices for text_list: %s", text_list)
                for text in text_list:
                    found_invoices = self.env['account.move'].search([("name", "ilike", text),("state", "=", "posted")])
                    _logger.debug("Found %s invoices for search '%s'", len(found_invoices), text)
                    invoice_ids |= found_invoices
                partner_ids = invoice_ids.partner_id if invoice_ids else partner_bank_id.partner_id
                payment_vals = {
                    "payment_type": "inbound" if credit else "outbound",
                    "partner_type": "customer" if credit else "supplier",
                    "amount": credit if credit else debit,
                    "date": accounting_date,
                    "journal_id": journal_id,
                    "currency_id": 23,
                    "partner_id": partner_ids[0].id if partner_ids else False,
                    "ref": ref,
                    "ref_src": ref,
                    "transaction_code": transaction_number,
                    "acc_counterpart_no": counterpart_account,
                    "acc_counterpart_name": counterpart_name,
                }
                _logger.info("Creating payment with values: %s", payment_vals)
                payment = self.env['account.payment'].create(payment_vals)
                _logger.info("Created payment with id %s, name %s", payment.id, payment.name)
                if payment.partner_id:
                    payment.action_post()
                    _logger.info("Posted payment id %s", payment.id)
                if credit:
                    move_line = payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                    if move_line and invoice_ids:
                        _logger.info("Assigning outstanding line: move_line id %s, invoice_ids: %s", move_line.id, invoice_ids.ids)
                        invoice_ids.js_assign_outstanding_line(move_line.id)
                result.append(payment.transaction_code)
        except Exception as e:
            _logger.error("Error in action_create_payment_from_automation_bank: %s", traceback.format_exc())
        return result

    def _check_transaction_exists(self, transaction_number):
        existing_payments = self.env['account.payment'].search([("transaction_code", "=", transaction_number)], limit=1)
        return bool(existing_payments)
