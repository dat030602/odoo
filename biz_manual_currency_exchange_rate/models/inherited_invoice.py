# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Sitaram Solutions (<https://sitaramsolutions.in/>).
#
#    For Module Support : info@sitaramsolutions.in  or Skype : contact.hiren1188
#
##############################################################################

from odoo import models, fields, api
from contextlib import contextmanager



class AccountMove(models.Model):
    _inherit = 'account.move'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate', digits=(12, 12))
    active_manual_currency_rate = fields.Boolean('active Manual Currency')
    is_invisible = fields.Boolean(compute='_check_is_invisible')
    inverse_manural_currency_exchange_rate = fields.Float(string='Inverse Manual Currency Exchange Rate', digits=(12, 2))

    def update_old_payment(self):
        for res in self.filtered(lambda x: x.payment_id):
            move_id = False
            if len(res.payment_id.reconciled_invoice_ids) == 1:
                move_id = res.payment_id.reconciled_invoice_ids[0]
            if len(res.payment_id.reconciled_bill_ids) == 1:
                move_id = res.payment_id.reconciled_bill_ids[0]
            if move_id and move_id.apply_manual_currency_exchange:
                res.write({
                        'apply_manual_currency_exchange': move_id.apply_manual_currency_exchange,
                        'manual_currency_exchange_rate': move_id.manual_currency_exchange_rate,
                        'active_manual_currency_rate': move_id.active_manual_currency_rate,
                        'inverse_manural_currency_exchange_rate': move_id.inverse_manural_currency_exchange_rate,
                    })
                for line in self.line_ids:
                    line.with_context(check_move_validity=False,update_old_payment=True).balance = (line.amount_currency * move_id.inverse_manural_currency_exchange_rate) if move_id.inverse_manural_currency_exchange_rate > 0 else (line.amount_currency / move_id.manual_currency_exchange_rate)
                    
    def update_exchange_rate_old_account_move(self):
        for res in self:
            if res.apply_manual_currency_exchange:
                res.invoice_line_ids._compute_currency_rate()

    def action_register_payment(self):
        action = super(AccountMove,self).action_register_payment()
        if action.get('context'):
            action['context'].update({'default_inverse_manural_currency_exchange_rate': self.inverse_manural_currency_exchange_rate})
        return action

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

    @api.onchange('company_id', 'currency_id')
    def onchange_currency_id(self):
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    @api.onchange("purchase_vendor_bill_id", "purchase_id")
    def _onchange_purchase_auto_complete(self):
        """Load from either an old purchase order, either an old vendor bill.

        When setting a 'purchase.bill.union' in 'purchase_vendor_bill_id':
        * If it's a vendor bill, 'invoice_vendor_bill_id' is set and the loading is done by '_onchange_invoice_vendor_bill'.
        * If it's a purchase order, 'purchase_id' is set and this method will load lines.

        /!\\ All this not-stored fields must be empty at the end of this function.
        """
        if self.purchase_vendor_bill_id.vendor_bill_id:
            self.invoice_vendor_bill_id = self.purchase_vendor_bill_id.vendor_bill_id
            self._onchange_invoice_vendor_bill()
        elif self.purchase_vendor_bill_id.purchase_order_id:
            self.purchase_id = self.purchase_vendor_bill_id.purchase_order_id
        self.purchase_vendor_bill_id = False

        if not self.purchase_id:
            return

        # Copy data from PO
        invoice_vals = self.purchase_id.with_company(
            self.purchase_id.company_id
        )._prepare_invoice()
        del invoice_vals["ref"]
        self.update(invoice_vals)

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.line_ids.mapped(
            "purchase_line_id"
        )
        new_lines = self.env["account.move.line"]
        for line in po_lines.filtered(lambda l: not l.display_type):
            new_line = new_lines.new(line._prepare_account_move_line(self))
            new_line.account_id = new_line._get_computed_account()
            new_line._onchange_price_subtotal()
            new_lines += new_line
        new_lines._onchange_mark_recompute_taxes()

        # Compute invoice_origin.
        origins = set(self.line_ids.mapped("purchase_line_id.order_id.name"))
        self.invoice_origin = ",".join(list(origins))

        # Compute ref.
        refs = self._get_invoice_reference()
        self.ref = ", ".join(refs)

        # Compute payment_reference.
        if len(refs) == 1:
            self.payment_reference = refs[0]

        self.purchase_id = False
        self._onchange_currency()

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            return base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=move.always_tax_exigible,
            )

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue
            if self.apply_manual_currency_exchange:
                balance = (taxes_map_entry['amount'] * self.inverse_manural_currency_exchange_rate) if self.inverse_manural_currency_exchange_rate > 0 else (taxes_map_entry['amount'] / self.manual_currency_exchange_rate)
            else:
                balance = currency._convert(
                    taxes_map_entry['amount'],
                    self.company_currency_id,
                    self.company_id,
                    self.date or fields.Date.context_today(self),
                )
            to_write_on_line = {
                'amount_currency': taxes_map_entry['amount'],
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'company_id': self.company_id.id,
                    'company_currency_id': self.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    @api.depends('currency_id', 'company_id', 'move_id.date', 'move_id.apply_manual_currency_exchange', 'move_id.inverse_manural_currency_exchange_rate',)
    def _compute_currency_rate(self):
        super(AccountMoveLine,self)._compute_currency_rate()
        for line in self:
            if line.move_id and line.move_id.apply_manual_currency_exchange and line.move_id.inverse_manural_currency_exchange_rate:
                line.currency_rate = line.move_id.inverse_manural_currency_exchange_rate

    #Not for used
    #@api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        ''' This method is used to recompute the values of 'amount_currency', 'debit', 'credit' due to a change made
        in some business fields (affecting the 'price_subtotal' field).

        :param price_subtotal:  The untaxed amount.
        :param move_type:       The type of the move.
        :param currency:        The line's currency.
        :param company:         The move's company.
        :param date:            The move's date.
        :return:                A dictionary containing 'debit', 'credit', 'amount_currency'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1

        amount_currency = price_subtotal * sign
        if self.move_id.apply_manual_currency_exchange:
            balance = (amount_currency * self.move_id.inverse_manural_currency_exchange_rate) if self.move_id.inverse_manural_currency_exchange_rate > 0 else (amount_currency / self.move_id.manual_currency_exchange_rate)

        else:
            balance = currency._convert(amount_currency, company.currency_id, company,
                                        date or fields.Date.context_today(self))
        return {
            'amount_currency': amount_currency,
            'currency_id': currency.id,
            'debit': balance > 0.0 and balance or 0.0,
            'credit': balance < 0.0 and -balance or 0.0,
        }

    @api.onchange('product_uom_id')
    def _onchange_uom_id(self):
        ''' Recompute the 'price_unit' depending of the unit of measure. '''
        if self.display_type in ('line_section', 'line_note'):
            return
        if self.product_id and self.product_id.lst_price:
            price_unit = self.product_id.lst_price
        else:
            price_unit = self._compute_price_unit()
        taxes = self._get_computed_taxes()
        if taxes and self.move_id.fiscal_position_id:
            taxes = self.move_id.fiscal_position_id.map_tax(taxes)
            price_subtotal = self._get_price_total_and_subtotal(
                price_unit=price_unit, taxes=taxes
            )["price_subtotal"]
            accounting_vals = self._get_fields_onchange_subtotal(
                price_subtotal=price_subtotal, currency=self.move_id.company_currency_id
            )
            amount_currency = accounting_vals["amount_currency"]
            price_unit = self._get_fields_onchange_balance(
                amount_currency=amount_currency, force_computation=True
            ).get("price_unit", price_unit)
        self.tax_ids = taxes
        
        #self.price_unit = self.with_context(manual_rate=self.move_id.manual_currency_exchange_rate,
        #active_manutal_currency=self.move_id.apply_manual_currency_exchange)._get_computed_price_unit()
        
        # Convert the unit price to the invoice's currency.
        company = self.move_id.company_id
        if self.move_id.apply_manual_currency_exchange and price_unit:
            self.price_unit = (price_unit * self.move_id.manual_currency_exchange_rate) if self.move_id.manual_currency_exchange_rate > 0 else 0
        else:
            self.price_unit = company.currency_id._convert(
                price_unit,
                self.move_id.currency_id,
                company,
                self.move_id.date,
                round=False,
            )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            #line.name = line._get_computed_name()
            #line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes)
            line.tax_ids = taxes
            #line.product_uom_id = line._get_computed_uom()
            line.product_uom_id = line._compute_product_uom_id()
            #line.price_unit = line.with_context(manual_rate=line.move_id.manual_currency_exchange_rate,
            #active_manutal_currency=line.move_id.apply_manual_currency_exchange)._get_computed_price_unit()
            if line.product_id and line.product_id.lst_price:
                price_unit = line.product_id.lst_price
            else:
                price_unit = line._compute_price_unit()
            
            # Convert the unit price to the invoice's currency.
            company = line.move_id.company_id
            if line.move_id.apply_manual_currency_exchange and price_unit:
                line.price_unit = (
                    price_unit * line.move_id.manual_currency_exchange_rate
                ) if self.move_id.manual_currency_exchange_rate > 0 else 0
            else:
                line.price_unit = company.currency_id._convert(
                    line.price_unit,
                    line.move_id.currency_id,
                    company,
                    line.move_id.date,
                    round=False,
                )

    @contextmanager
    def _sync_invoice(self, container):
        if container['records'].env.context.get('skip_sync_invoice'):
            yield
            return  # avoid infinite recursion

        def existing():
            return {
                line: {
                    'amount_currency': line.currency_id.round(line.amount_currency),
                    'balance': line.company_id.currency_id.round(line.balance),
                    'currency_rate': line.currency_rate,
                    'price_subtotal': line.currency_id.round(line.price_subtotal),
                    'move_type': line.move_id.move_type,
                } for line in container['records'].with_context(
                    skip_sync_invoice=True,
                ).filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        yield
        after = existing()
        for line in after:
            if (
                line.display_type == 'product'
                and (not changed('amount_currency') or line not in before)
            ):
                amount_currency = line.move_id.direction_sign * line.currency_id.round(line.price_subtotal)
                if not line.create_in_detail_move:
                    if line.amount_currency != amount_currency or line not in before:
                        line.amount_currency = amount_currency
                    if line.currency_id == line.company_id.currency_id:
                        line.balance = amount_currency

        after = existing()
        for line in after:
            if (
                (changed('amount_currency') or changed('currency_rate') or changed('move_type'))
                and (not changed('balance') or (line not in before and not line.balance))
            ):
                balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
                if line.move_id.apply_manual_currency_exchange:
                    balance = (line.amount_currency * line.move_id.inverse_manural_currency_exchange_rate) if line.move_id.inverse_manural_currency_exchange_rate > 0 else (line.amount_currency / line.move_id.manual_currency_exchange_rate)
                line.balance = balance
        # Since this method is called during the sync, inside of `create`/`write`, these fields
        # already have been computed and marked as so. But this method should re-trigger it since
        # it changes the dependencies.
        self.env.add_to_compute(self._fields['debit'], container['records'])
        self.env.add_to_compute(self._fields['credit'], container['records'])

    #Not for Used
    #@api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        for line in self:
            company = line.move_id.company_id
            if line.move_id.apply_manual_currency_exchange:
                balance = (line.amount_currency * line.move_id.inverse_manural_currency_exchange_rate) if line.move_id.inverse_manural_currency_exchange_rate > 0 else (line.amount_currency / line.move_id.manual_currency_exchange_rate)
            else:
                balance = line.currency_id._convert(line.amount_currency, company.currency_id, company,
                                                    line.move_id.date)
            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())

    def _get_lock_date_protected_fields(self):
        protected_fields = super()._get_lock_date_protected_fields()
        if self._context.get('update_old_payment'):
            protected_fields['reconciliation'].remove('balance')
        return protected_fields