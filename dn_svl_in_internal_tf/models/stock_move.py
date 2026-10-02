# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""stock.move - Generate SVL & Journal Entry for internal warehouse transfers.

Flow
====
1. ``_action_done`` calls ``_create_internal_transfer_svl`` after super().
2. ``_is_internal_transfer`` - guards activation:
   * The ``group_internal_transfer_valuation`` flag is enabled.
   * Both source and destination have ``usage == 'internal'``.
   * The product has ``valuation == 'real_time'`` (perpetual).
3. ``_create_internal_transfer_svl`` - creates 2 SVL records (negative OUT + positive IN).
4. ``_create_internal_transfer_account_move`` - creates & posts a Journal Entry
   (only when debit_account is different from credit_account).
"""

from odoo import _, api, fields, models, Command
from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    stock_valuation_layer_ids = fields.One2many(
        'stock.valuation.layer',
        'stock_move_id',
        string='Stock Valuation Layers',
    )

    # -------------------------------------------------------------------------
    # Helpers - condition check
    # -------------------------------------------------------------------------

    def _is_internal_transfer(self):
        """Return True when this move is an internal transfer that requires valuation.

        All conditions must be met simultaneously:
        * The ``group_internal_transfer_valuation`` configuration flag is enabled.
        * ``location_id.usage == 'internal'``.
        * ``location_dest_id.usage == 'internal'``.
        * ``product_id.valuation == 'real_time'`` (perpetual/automatic valuation).
        """
        self.ensure_one()

        # Check the feature flag
        feature_enabled = self.env.user.has_group(
            'dn_svl_in_internal_tf.group_internal_transfer_valuation'
        )
        if not feature_enabled:
            return False

        if self.location_id.usage != 'internal':
            return False
        if self.location_dest_id.usage != 'internal':
            return False

        # Product must use automated (perpetual) valuation
        product = self.product_id.with_company(self.company_id)
        if product.valuation != 'real_time':
            return False

        return True

    # -------------------------------------------------------------------------
    # Override _action_done
    # -------------------------------------------------------------------------

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        moves._create_internal_transfer_svl()
        return moves

    # -------------------------------------------------------------------------
    # SVL creation
    # -------------------------------------------------------------------------

    def _create_internal_transfer_svl(self):
        """Create an OUT/IN SVL pair for each qualifying internal transfer move."""
        SVL = self.env['stock.valuation.layer']
        for move in self:
            if not move._is_internal_transfer():
                continue

            qty = move._get_internal_transfer_qty()
            if float_is_zero(qty, precision_rounding=move.product_uom.rounding):
                continue

            unit_cost = move._get_internal_transfer_unit_cost()
            value = unit_cost * qty

            description = _(
                'Internal transfer: %(ref)s', ref=move.reference or move.description_picking or move.product_id.display_name
            )

            # Layer 1 - Source location OUT (negative)
            svl_out = SVL.sudo().create({
                'product_id': move.product_id.id,
                'quantity': -qty,
                'uom_id': move.product_id.uom_id.id,
                'unit_cost': unit_cost,
                'value': -value,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': description,
            })

            # Layer 2 - Destination location IN (positive)
            svl_in = SVL.sudo().create({
                'product_id': move.product_id.id,
                'quantity': qty,
                'uom_id': move.product_id.uom_id.id,
                'unit_cost': unit_cost,
                'value': value,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': description,
            })

            # Create a Journal Entry when the two accounts differ
            move._create_internal_transfer_account_move(svl_out, svl_in)

    def _get_internal_transfer_qty(self):
        """Return the transferred quantity in the product's UoM."""
        self.ensure_one()
        qty = sum(
            ml.quantity_product_uom
            for ml in self.move_line_ids
            if ml.picked and not ml._should_exclude_for_valuation()
        )
        if not qty:
            qty = self.product_uom._compute_quantity(
                self.quantity, self.product_id.uom_id
            )
        return qty

    def _get_internal_transfer_unit_cost(self):
        """Return the current standard cost of the product for this company."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        return product.standard_price

    # -------------------------------------------------------------------------
    # Journal Entry creation
    # -------------------------------------------------------------------------

    def _get_internal_transfer_accounts(self):
        """Return (credit_account, debit_account) for the internal transfer.

        * ``credit_account``: valuation account of the source location.
        * ``debit_account``:  valuation account of the destination location.

        Resolution: per-location account -> parent hierarchy -> product category.
        """
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        credit_account = self.location_id._get_valuation_account(product)
        debit_account = self.location_dest_id._get_valuation_account(product)
        return credit_account, debit_account

    def _create_internal_transfer_account_move(self, svl_out, svl_in):
        """Create and post a Journal Entry for the internal transfer.

        Skipped when:
        * Either account is missing.
        * Both accounts are identical (no ledger impact - avoids noise entries).

        After posting, ``account_move_id`` is written on both SVL records
        for full audit traceability.
        """
        self.ensure_one()
        credit_account, debit_account = self._get_internal_transfer_accounts()

        # Skip if accounts are missing or identical
        if not credit_account or not debit_account:
            return
        if credit_account.id == debit_account.id:
            return

        value = abs(svl_in.value)
        if float_is_zero(value, precision_rounding=self.company_id.currency_id.rounding):
            return

        ref = _('Internal Transfer: %(ref)s', ref=self.reference or self.description_picking or self.product_id.display_name)
        product_name = self.product_id.display_name

        journal = self.company_id.account_stock_journal_id
        if not journal:
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.company_id.id),
                ('type', '=', 'general'),
            ], limit=1)
        if not journal:
            return

        account_move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'ref': ref,
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'line_ids': [
                Command.create({
                    'account_id': credit_account.id,
                    'name': ref + ' - ' + product_name,
                    'debit': 0.0,
                    'credit': value,
                    'product_id': self.product_id.id,
                }),
                Command.create({
                    'account_id': debit_account.id,
                    'name': ref + ' - ' + product_name,
                    'debit': value,
                    'credit': 0.0,
                    'product_id': self.product_id.id,
                }),
            ],
        })
        account_move._post()

        # Link both SVL records to the posted journal entry for traceability
        (svl_out | svl_in).sudo().write({'account_move_id': account_move.id})


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_valuation_layer_ids = fields.One2many(
        'stock.valuation.layer',
        'account_move_id',
        string='Stock Valuation Layers',
    )
