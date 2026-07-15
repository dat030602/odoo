# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Sitaram Solutions (<https://sitaramsolutions.in/>).
#
#    For Module Support : info@sitaramsolutions.in  or Skype : contact.hiren1188
#
##############################################################################

from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError


class AccountPayments(models.Model):
    _inherit = 'account.payment'

    apply_manual_currency_exchange = fields.Boolean(
        string='Apply Manual Currency Exchange')
    manual_currency_exchange_rate = fields.Float(
        string='Manual Currency Exchange Rate', digits=(12, 12))
    active_manual_currency_rate = fields.Boolean(
        'active Manual Currency', default=False)
    is_invisible = fields.Boolean(compute='_check_is_invisible')
    inverse_manural_currency_exchange_rate = fields.Float(string='Inverse Manual Currency Exchange Rate', digits=(12, 2))
    
    def _synchronize_to_moves_exchange(self):
        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            write_off_line_vals = []
            if liquidity_lines and counterpart_lines and writeoff_lines:
                write_off_line_vals.append({
                    'name': writeoff_lines[0].name,
                    'account_id': writeoff_lines[0].account_id.id,
                    'partner_id': writeoff_lines[0].partner_id.id,
                    'currency_id': writeoff_lines[0].currency_id.id,
                    'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
                    'balance': sum(writeoff_lines.mapped('balance')),
                })
                
            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
            line_ids_commands = [
                Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
            ]

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))
            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))

            pay.move_id\
                .with_context(skip_invoice_sync=True)\
                .write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                })
    
    def write(self, vals):
        res = super(AccountPayments, self).write(vals)
        if 'inverse_manural_currency_exchange_rate' in vals and self.move_id:
            self.move_id.apply_manual_currency_exchange = True
            self.move_id.manual_currency_exchange_rate = self.manual_currency_exchange_rate
            self.move_id.inverse_manural_currency_exchange_rate = self.inverse_manural_currency_exchange_rate
            
            self._synchronize_to_moves_exchange()
                
        return res

    @api.depends('apply_manual_currency_exchange', 'active_manual_currency_rate')
    def _check_is_invisible(self):
        is_debug = self.user_has_groups('base.group_no_one')
        is_inverse = self.company_id.currency_id.is_inverse
        
        if is_inverse:
            if is_debug:
                self.is_invisible = False
            else:
                self.is_invisible = True
        else:
            self.is_invisible = False
    
    @api.onchange('inverse_manural_currency_exchange_rate')
    def onchange_inverse_manural_currency_exchange_rate(self):
        self.manual_currency_exchange_rate = (1 / self.inverse_manural_currency_exchange_rate) if self.inverse_manural_currency_exchange_rate > 0 else 0

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        if self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or []
        if isinstance(write_off_line_vals, dict):
            write_off_line_vals_list = [write_off_line_vals]
        else:
            write_off_line_vals_list = write_off_line_vals

        if not self.outstanding_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                self.payment_method_line_id.name, self.journal_id.display_name))

        # Compute amounts.
        write_off_amount_currency = sum(x.get('amount_currency', x.get('amount', 0.0)) for x in write_off_line_vals_list)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
            write_off_amount_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = 0.0

        if self.active_manual_currency_rate:
            if self.apply_manual_currency_exchange:
                liquidity_balance = (liquidity_amount_currency * self.inverse_manural_currency_exchange_rate) if self.inverse_manural_currency_exchange_rate > 0 else (liquidity_amount_currency / self.manual_currency_exchange_rate)
                write_off_balance = (write_off_amount_currency * self.inverse_manural_currency_exchange_rate) if self.inverse_manural_currency_exchange_rate > 0 else (write_off_amount_currency / self.manual_currency_exchange_rate)
            else:
                write_off_balance = self.currency_id._convert(
                    write_off_amount_currency,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
                liquidity_balance = self.currency_id._convert(
                    liquidity_amount_currency,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
        else:
            write_off_balance = self.currency_id._convert(
                write_off_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else:  # payment.payment_type == 'outbound':
                liquidity_line_name = _(
                    'Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }

        # default_line_name = self.env['account.move.line']._get_default_line_name(
        #     _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
        #     self.amount,
        #     self.currency_id,
        #     self.date,
        #     partner=self.partner_id,
        # )

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.outstanding_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': self.payment_reference,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        if not self.currency_id.is_zero(write_off_amount_currency):
            # Write-off line.
            for wo_vals in write_off_line_vals_list:
                wo_amount_currency = wo_vals.get('amount_currency', wo_vals.get('amount', 0.0))
                # Calculate the proportionate balance for this write-off line
                ratio = (wo_amount_currency / write_off_amount_currency) if write_off_amount_currency else 0.0
                wo_balance = write_off_balance * ratio
                line_vals_list.append({
                    'name': wo_vals.get('name') or False,
                    'amount_currency': wo_amount_currency,
                    'currency_id': currency_id,
                    'debit': wo_balance if wo_balance > 0.0 else 0.0,
                    'credit': -wo_balance if wo_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': wo_vals.get('account_id'),
                })
        return line_vals_list
