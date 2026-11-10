# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""stock.move - Extension for Internal Transfer Valuation and Move Type Filtering."""

from odoo import _, fields, models
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    # -------------------------------------------------------------------------
    # Classification & Move Type Filtering
    # -------------------------------------------------------------------------

    def _is_internal_transfer(self):
        """Check if move is an internal transfer eligible for valuation."""
        self.ensure_one()
        if self._get_valuation_move_type_key() != 'internal_transfer':
            return False
        product = self.product_id.with_company(self.company_id)
        if not product.is_storable or product.valuation != 'real_time':
            return False
        return 'internal_transfer' in self.company_id.auto_svl_move_type_ids.mapped('key')

    def _should_create_in_svl(self):
        """Filter incoming SVL creation based on company auto_svl_move_type_ids."""
        if self.company_id.auto_svl_move_type_ids:
            return 'receipt' in self.company_id.auto_svl_move_type_ids.mapped('key')
        return super()._should_create_in_svl()

    def _should_create_out_svl(self):
        """Filter outgoing SVL creation based on company auto_svl_move_type_ids."""
        if self.company_id.auto_svl_move_type_ids:
            return 'delivery' in self.company_id.auto_svl_move_type_ids.mapped('key')
        return super()._should_create_out_svl()

    # -------------------------------------------------------------------------
    # Internal Transfer SVL Creation
    # -------------------------------------------------------------------------

    def _create_internal_transfer_svl(self, forced_quantity=None):
        """Create paired Stock Valuation Layers for internal transfer moves."""
        svl_vals_list = []
        for move in self:
            qty = forced_quantity if forced_quantity is not None else move._get_move_quantity()
            if float_is_zero(qty, precision_rounding=move.product_uom.rounding):
                continue

            product = move.product_id.with_company(move.company_id)
            unit_cost = product.standard_price
            value = move.company_id.currency_id.round(qty * unit_cost)
            description = _(
                'Internal transfer: %(ref)s',
                ref=move.reference or move.description_picking or move.product_id.display_name,
            )

            # Layer 1: Source location OUT (negative)
            svl_vals_list.append({
                'product_id': move.product_id.id,
                'quantity': -qty,
                'uom_id': move.product_id.uom_id.id,
                'unit_cost': unit_cost,
                'value': -value,
                'remaining_qty': 0.0,
                'remaining_value': 0.0,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': description,
                'date': move.date or fields.Datetime.now(),
            })

            # Layer 2: Destination location IN (positive)
            svl_vals_list.append({
                'product_id': move.product_id.id,
                'quantity': qty,
                'uom_id': move.product_id.uom_id.id,
                'unit_cost': unit_cost,
                'value': value,
                'remaining_qty': 0.0,
                'remaining_value': 0.0,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': description,
                'date': move.date or fields.Datetime.now(),
            })

        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _get_interim_transit_account(self):
        """Return transit/interim account for balancing internal transfer entries."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        accounts = product._get_product_accounts()
        transit_account = (
            accounts.get('stock_variation')
            or accounts.get('stock_input')
            or accounts.get('stock_output')
            or getattr(self.company_id, 'account_stock_variation_id', self.env['account.account'])
            or product.categ_id.property_stock_valuation_account_id
        )
        return transit_account

    def _get_internal_transfer_accounts(self):
        """Return (credit_account, debit_account) for internal transfer."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        debit_account = self.location_dest_id._get_valuation_account(product)
        credit_account = self.location_id._get_valuation_account(product)
        return credit_account, debit_account

    # -------------------------------------------------------------------------
    # Override _action_done & _account_entry_move
    # -------------------------------------------------------------------------

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        moves_internal = moves.filtered(lambda m: m._is_internal_transfer())
        if moves_internal:
            stock_valuation_layers = moves_internal._create_internal_transfer_svl()
            if stock_valuation_layers:
                stock_valuation_layers._validate_accounting_entries()
        return moves

    def _account_entry_move(self, qty, description, svl_id, cost):
        """Prepare journal entry values with transit account for internal transfers."""
        self.ensure_one()
        company = self.company_id

        if self._is_internal_transfer():
            abs_cost = abs(cost)
            if float_is_zero(abs_cost, precision_rounding=company.currency_id.rounding):
                return []

            if 'internal_transfer' not in company.auto_je_move_type_ids.mapped('key'):
                return []

            credit_account, debit_account = self._get_internal_transfer_accounts()
            transit_account = self._get_interim_transit_account()
            if not credit_account or not debit_account or not transit_account:
                return []

            journal_id, _, _, _ = self._get_accounting_data_for_valuation()
            if not journal_id:
                return []

            svl = self.env['stock.valuation.layer'].browse(svl_id) if svl_id else None
            entry_date = (
                fields.Date.context_today(self, svl.date)
                if svl and svl.date
                else fields.Date.context_today(self)
            )

            base_ref = description or self.reference or self.name or self.product_id.display_name
            if qty < 0:
                ref = f"{base_ref} - OUT"
                vals = self._prepare_account_move_vals(
                    credit_account.id, transit_account.id, journal_id, qty, ref, svl_id, abs_cost, date=entry_date
                )
                return [vals]
            else:
                ref = f"{base_ref} - IN"
                vals = self._prepare_account_move_vals(
                    transit_account.id, debit_account.id, journal_id, qty, ref, svl_id, abs_cost, date=entry_date
                )
                return [vals]

        # Receipt or Delivery: check auto_je_move_type_ids if auto_svl_move_type_ids is configured
        if company.auto_svl_move_type_ids:
            je_keys = set(company.auto_je_move_type_ids.mapped('key'))
            if self._is_in() and 'receipt' not in je_keys:
                return []
            if self._is_out() and 'delivery' not in je_keys:
                return []

        return super()._account_entry_move(qty, description, svl_id, cost)

    # -------------------------------------------------------------------------
    # Internal Transfer Done Move Modification
    # -------------------------------------------------------------------------

    def _handle_valuation_quantity_change(self, old_qty, new_qty):
        """Handle valuation modification for internal transfers."""
        self.ensure_one()
        if not self._is_internal_transfer():
            return super()._handle_valuation_quantity_change(old_qty, new_qty)

        if self.env.context.get('skip_valuation_adjust'):
            return

        if not self.env.user.has_group('stock.group_stock_manager') and not self.env.is_superuser():
            raise UserError(_("Only Stock Managers are allowed to modify quantities on completed stock moves."))

        datetime_val, date_val = self._get_valuation_modification_datetime()
        self._check_lock_date(date_val)

        delta_qty = new_qty - old_qty
        if float_is_zero(delta_qty, precision_rounding=self.product_uom.rounding):
            return

        mode = self.company_id.svl_modification_mode or 'create_diff'
        if mode == 'create_diff':
            unit_cost = self.product_id.with_company(self.company_id).standard_price
            abs_qty = abs(delta_qty)
            abs_val = self.company_id.currency_id.round(abs_qty * unit_cost)

            if delta_qty > 0:
                svl_vals_list = [
                    {
                        'product_id': self.product_id.id,
                        'quantity': -abs_qty,
                        'uom_id': self.product_id.uom_id.id,
                        'unit_cost': unit_cost,
                        'value': -abs_val,
                        'remaining_qty': 0.0,
                        'remaining_value': 0.0,
                        'stock_move_id': self.id,
                        'company_id': self.company_id.id,
                        'description': _('Adjustment (Increase OUT): %(ref)s', ref=self.reference or self.name),
                        'date': datetime_val,
                    },
                    {
                        'product_id': self.product_id.id,
                        'quantity': abs_qty,
                        'uom_id': self.product_id.uom_id.id,
                        'unit_cost': unit_cost,
                        'value': abs_val,
                        'remaining_qty': 0.0,
                        'remaining_value': 0.0,
                        'stock_move_id': self.id,
                        'company_id': self.company_id.id,
                        'description': _('Adjustment (Increase IN): %(ref)s', ref=self.reference or self.name),
                        'date': datetime_val,
                    },
                ]
            else:
                svl_vals_list = [
                    {
                        'product_id': self.product_id.id,
                        'quantity': abs_qty,
                        'uom_id': self.product_id.uom_id.id,
                        'unit_cost': unit_cost,
                        'value': abs_val,
                        'remaining_qty': 0.0,
                        'remaining_value': 0.0,
                        'stock_move_id': self.id,
                        'company_id': self.company_id.id,
                        'description': _('Adjustment (Decrease OUT): %(ref)s', ref=self.reference or self.name),
                        'date': datetime_val,
                    },
                    {
                        'product_id': self.product_id.id,
                        'quantity': -abs_qty,
                        'uom_id': self.product_id.uom_id.id,
                        'unit_cost': unit_cost,
                        'value': -abs_val,
                        'remaining_qty': 0.0,
                        'remaining_value': 0.0,
                        'stock_move_id': self.id,
                        'company_id': self.company_id.id,
                        'description': _('Adjustment (Decrease IN): %(ref)s', ref=self.reference or self.name),
                        'date': datetime_val,
                    },
                ]

            new_svls = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
            new_svls._validate_accounting_entries()

            if self.company_id.svl_modification_date_mode == 'picking_date':
                self.with_context(skip_valuation_adjust=True).write({'date': datetime_val})
                self.move_line_ids.with_context(skip_valuation_adjust=True).write({'date': datetime_val})

            if self.picking_id:
                jes = new_svls.account_move_id
                self.picking_id.message_post(body=_(
                    "Valuation Adjustment for internal transfer move %(move)s: quantity changed from %(old)s to %(new)s %(uom)s.<br/>"
                    "Layers created: %(svls)s.<br/>"
                    "Journal entries created: %(jes)s.",
                    move=self.reference or self.name,
                    old=old_qty,
                    new=new_qty,
                    uom=self.product_uom.name,
                    svls=", ".join(map(str, new_svls.ids)),
                    jes=", ".join(jes.mapped('name')) if jes else "None",
                ))

        elif mode == 'update_existing':
            svls = self.stock_valuation_layer_ids.filtered(lambda l: l.quantity != 0)
            svl_out = svls.filtered(lambda l: l.quantity < 0)
            svl_in = svls.filtered(lambda l: l.quantity > 0)
            if not svl_out or not svl_in:
                # Fallback to diff
                self.company_id.svl_modification_mode = 'create_diff'
                self._handle_valuation_quantity_change(old_qty, new_qty)
                self.company_id.svl_modification_mode = 'update_existing'
                return

            orig_out = svl_out[0]
            orig_in = svl_in[0]
            unit_cost = orig_out.unit_cost
            new_val = self.company_id.currency_id.round(new_qty * unit_cost)

            orig_out.write({'quantity': -new_qty, 'value': -new_val, 'date': datetime_val})
            orig_in.write({'quantity': new_qty, 'value': new_val, 'date': datetime_val})

            self._update_existing_account_moves(orig_out, date_val)
            self._update_existing_account_moves(orig_in, date_val)

            if self.company_id.svl_modification_date_mode == 'picking_date':
                self.with_context(skip_valuation_adjust=True).write({'date': datetime_val})
                self.move_line_ids.with_context(skip_valuation_adjust=True).write({'date': datetime_val})

            if self.picking_id:
                self.picking_id.message_post(body=_(
                    "Valuation Update for internal transfer move %(move)s: quantity updated from %(old)s to %(new)s %(uom)s.<br/>"
                    "Updated layers %(out_id)s and %(in_id)s.",
                    move=self.reference or self.name,
                    old=old_qty,
                    new=new_qty,
                    uom=self.product_uom.name,
                    out_id=orig_out.id,
                    in_id=orig_in.id,
                ))
