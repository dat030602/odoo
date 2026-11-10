# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""stock.move - Core Valuation Layer & Costing Engine for Odoo 19.

Implements Standard, AVCO, FIFO costing methods, automated SVL and Journal Entry
generation for incoming/outgoing moves, and handling of quantity modifications
on completed (done) moves.
"""

from collections import defaultdict
from odoo import _, api, fields, models, Command
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    stock_valuation_layer_ids = fields.One2many(
        'stock.valuation.layer',
        'stock_move_id',
        string='Stock Valuation Layers',
    )
    dn_svl_count = fields.Integer(
        string='Valuation Layers',
        compute='_compute_dn_svl_count',
    )

    def _compute_dn_svl_count(self):
        for move in self:
            move.dn_svl_count = len(move.sudo().stock_valuation_layer_ids)

    def action_dn_view_svl(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Valuation Layers'),
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,form',
            'domain': [('stock_move_id', '=', self.id)],
        }

    # -------------------------------------------------------------------------
    # Move classification & conditions
    # -------------------------------------------------------------------------

    def _get_valuation_move_type_key(self):
        """Determine move type key ('receipt', 'delivery', 'internal_transfer', or False)."""
        self.ensure_one()
        src_usage = self.location_id.usage
        dest_usage = self.location_dest_id.usage
        if src_usage == 'internal' and dest_usage == 'internal':
            return 'internal_transfer'
        if src_usage != 'internal' and dest_usage == 'internal':
            return 'receipt'
        if src_usage == 'internal' and dest_usage != 'internal':
            return 'delivery'
        return False

    def _is_in(self):
        """Check if move is incoming."""
        self.ensure_one()
        return self._get_valuation_move_type_key() == 'receipt'

    def _is_out(self):
        """Check if move is outgoing."""
        self.ensure_one()
        return self._get_valuation_move_type_key() == 'delivery'

    def _is_internal_transfer(self):
        """Check if move is an internal transfer (overridden by extension module)."""
        self.ensure_one()
        return False

    def _should_create_in_svl(self):
        """Hook to decide if SVL should be created for incoming move."""
        self.ensure_one()
        return True

    def _should_create_out_svl(self):
        """Hook to decide if SVL should be created for outgoing move."""
        self.ensure_one()
        return True

    def _get_move_quantity(self):
        """Return the moved quantity in product UoM."""
        self.ensure_one()
        qty = sum(
            ml.quantity_product_uom
            for ml in self.move_line_ids
            if ml.picked and not ml._should_exclude_for_valuation()
        )
        if not qty:
            qty = self.product_uom._compute_quantity(self.quantity, self.product_id.uom_id)
        return qty

    # -------------------------------------------------------------------------
    # Costing Method Engine
    # -------------------------------------------------------------------------

    def _get_price_unit(self):
        """Resolve unit cost for incoming valuation layer."""
        self.ensure_one()
        # 1. Purchase line reference
        if hasattr(self, 'purchase_line_id') and self.purchase_line_id:
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.product_uom_id != self.product_id.uom_id:
                price_unit = line.product_uom_id._compute_price(price_unit, self.product_id.uom_id)
            if order.currency_id != self.company_id.currency_id:
                price_unit = order.currency_id._convert(
                    price_unit,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date or fields.Date.context_today(self),
                )
            return price_unit

        # 2. Return move reference
        if self.origin_returned_move_id:
            origin_layers = self.origin_returned_move_id.stock_valuation_layer_ids.filtered(
                lambda l: l.quantity != 0
            )
            if origin_layers:
                return abs(origin_layers[-1].unit_cost)

        # 3. Fallback to current standard price
        return self.product_id.with_company(self.company_id).standard_price

    def _create_in_svl(self, forced_quantity=None):
        """Create Stock Valuation Layer for incoming moves."""
        svl_vals_list = []
        for move in self:
            qty = forced_quantity if forced_quantity is not None else move._get_move_quantity()
            if float_is_zero(qty, precision_rounding=move.product_uom.rounding):
                continue

            product = move.product_id.with_company(move.company_id)
            cost_method = product.cost_method

            if cost_method == 'standard':
                unit_cost = product.standard_price
                value = move.company_id.currency_id.round(qty * unit_cost)
                rem_qty = 0.0
                rem_val = 0.0
            elif cost_method == 'average':
                unit_cost = move._get_price_unit()
                value = move.company_id.currency_id.round(qty * unit_cost)
                rem_qty = 0.0
                rem_val = 0.0
                move._recompute_product_avco(qty, value)
            elif cost_method == 'fifo':
                unit_cost = move._get_price_unit()
                value = move.company_id.currency_id.round(qty * unit_cost)
                rem_qty = qty
                rem_val = value
                product.sudo().write({'standard_price': unit_cost})
            else:
                unit_cost = product.standard_price
                value = move.company_id.currency_id.round(qty * unit_cost)
                rem_qty = 0.0
                rem_val = 0.0

            description = _(
                'Receipt: %(ref)s',
                ref=move.reference or move.description_picking or move.product_id.display_name,
            )
            svl_vals_list.append({
                'product_id': move.product_id.id,
                'quantity': qty,
                'uom_id': move.product_id.uom_id.id,
                'unit_cost': unit_cost,
                'value': value,
                'remaining_qty': rem_qty,
                'remaining_value': rem_val,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': description,
                'date': move.date or fields.Datetime.now(),
            })
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _create_out_svl(self, forced_quantity=None):
        """Create Stock Valuation Layer for outgoing moves."""
        svl_vals_list = []
        for move in self:
            qty = forced_quantity if forced_quantity is not None else move._get_move_quantity()
            if float_is_zero(qty, precision_rounding=move.product_uom.rounding):
                continue

            product = move.product_id.with_company(move.company_id)
            cost_method = product.cost_method

            if cost_method == 'standard':
                unit_cost = product.standard_price
                value = -move.company_id.currency_id.round(qty * unit_cost)
            elif cost_method == 'average':
                unit_cost = product.standard_price
                value = -move.company_id.currency_id.round(qty * unit_cost)
                # Check for inventory exhaustion rounding adjustment
                existing_svls = self.env['stock.valuation.layer'].sudo().search([
                    ('product_id', '=', product.id),
                    ('company_id', '=', move.company_id.id),
                ])
                current_qty = sum(existing_svls.mapped('quantity'))
                current_val = sum(existing_svls.mapped('value'))
                if float_is_zero(current_qty - qty, precision_rounding=product.uom_id.rounding):
                    value = -current_val
            elif cost_method == 'fifo':
                value, unit_cost = move._run_fifo(qty, move.company_id)
            else:
                unit_cost = product.standard_price
                value = -move.company_id.currency_id.round(qty * unit_cost)

            description = _(
                'Delivery: %(ref)s',
                ref=move.reference or move.description_picking or move.product_id.display_name,
            )
            svl_vals_list.append({
                'product_id': move.product_id.id,
                'quantity': -qty,
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

    def _run_fifo(self, quantity, company, lot=False):
        """Consume candidate valuation layers in FIFO order.

        :return: (negative_value, effective_unit_cost)
        """
        self.ensure_one()
        candidates = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', company.id),
            ('remaining_qty', '>', 0),
        ], order='create_date asc, id asc')

        remaining_needed = quantity
        total_value_taken = 0.0
        currency = company.currency_id

        for candidate in candidates:
            if remaining_needed <= 0:
                break
            qty_taken = min(remaining_needed, candidate.remaining_qty)
            cand_cost = (
                candidate.remaining_value / candidate.remaining_qty
                if candidate.remaining_qty else candidate.unit_cost
            )
            val_taken = currency.round(qty_taken * cand_cost)
            candidate.write({
                'remaining_qty': candidate.remaining_qty - qty_taken,
                'remaining_value': candidate.remaining_value - val_taken,
            })
            total_value_taken += val_taken
            remaining_needed -= qty_taken

        # Fallback for negative/short inventory
        if remaining_needed > 0:
            std_cost = self.product_id.with_company(company).standard_price
            extra_val = currency.round(remaining_needed * std_cost)
            total_value_taken += extra_val

        effective_unit_cost = (
            total_value_taken / quantity if quantity
            else self.product_id.with_company(company).standard_price
        )

        # Update product display cost with next active candidate
        next_cand = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', company.id),
            ('remaining_qty', '>', 0),
        ], order='create_date asc, id asc', limit=1)
        if next_cand:
            self.product_id.with_company(company).sudo().write({'standard_price': next_cand.unit_cost})

        return -total_value_taken, effective_unit_cost

    def _restore_fifo_candidates_on_decrease(self, quantity, company, lot=False):
        """Restore consumed candidate layers upon quantity decrease.

        :return: (restored_value, effective_unit_cost)
        """
        self.ensure_one()
        candidates = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', company.id),
            ('quantity', '>', 0),
        ], order='create_date desc, id desc')

        needed_to_restore = quantity
        restored_value = 0.0
        currency = company.currency_id

        for candidate in candidates:
            if needed_to_restore <= 0:
                break
            can_restore_qty = candidate.quantity - candidate.remaining_qty
            if can_restore_qty <= 0:
                continue
            qty_to_restore = min(needed_to_restore, can_restore_qty)
            val_to_restore = currency.round(qty_to_restore * candidate.unit_cost)
            candidate.write({
                'remaining_qty': candidate.remaining_qty + qty_to_restore,
                'remaining_value': candidate.remaining_value + val_to_restore,
            })
            restored_value += val_to_restore
            needed_to_restore -= qty_to_restore

        if needed_to_restore > 0:
            std_cost = self.product_id.with_company(company).standard_price
            extra_val = currency.round(needed_to_restore * std_cost)
            restored_value += extra_val

        effective_unit_cost = (
            restored_value / quantity if quantity
            else self.product_id.with_company(company).standard_price
        )
        return restored_value, effective_unit_cost

    def _recompute_product_avco(self, quantity, value):
        """Update product average cost on inbound movement."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        existing_svls = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', product.id),
            ('company_id', '=', self.company_id.id),
        ])
        curr_qty = sum(existing_svls.mapped('quantity'))
        curr_val = sum(existing_svls.mapped('value'))
        new_qty = curr_qty + quantity
        new_val = curr_val + value
        if new_qty > 0:
            new_price = new_val / new_qty
            product.sudo().write({'standard_price': new_price})

    def _recompute_product_avco_after_diff(self, delta_qty, value):
        """Update AVCO after adjustment diff layer."""
        self._recompute_product_avco(delta_qty, value)

    def _recompute_product_avco_after_adjustment(self, old_value, new_value, old_qty, new_qty):
        """Recompute AVCO after direct modification of an existing layer."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        existing_svls = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', product.id),
            ('company_id', '=', self.company_id.id),
        ])
        curr_qty = sum(existing_svls.mapped('quantity')) - old_qty + new_qty
        curr_val = sum(existing_svls.mapped('value')) - old_value + new_value
        if curr_qty > 0:
            new_price = curr_val / curr_qty
            product.sudo().write({'standard_price': new_price})

    # -------------------------------------------------------------------------
    # Accounting Entry Preparation & Resolution
    # -------------------------------------------------------------------------

    def _get_counterpart_account(self, location, product):
        """Return counterpart valuation account for a non-internal location."""
        loc = location
        while loc:
            if loc.dn_valuation_account_id:
                return loc.dn_valuation_account_id
            loc = loc.location_id or False
        accounts = product._get_product_accounts()
        return (
            accounts.get('stock_variation')
            or accounts.get('stock_valuation')
            or self.env['account.account']
        )

    def _get_valuation_accounts(self, move_type_key):
        """Return (debit_account, credit_account) according to move type."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        if move_type_key == 'receipt':
            debit_account = self.location_dest_id._get_valuation_account(product)
            credit_account = self._get_counterpart_account(self.location_id, product)
        elif move_type_key == 'delivery':
            debit_account = self._get_counterpart_account(self.location_dest_id, product)
            credit_account = self.location_id._get_valuation_account(product)
        elif move_type_key == 'internal_transfer':
            debit_account = self.location_dest_id._get_valuation_account(product)
            credit_account = self.location_id._get_valuation_account(product)
        else:
            return self.env['account.account'], self.env['account.account']
        return debit_account, credit_account

    def _get_accounting_data_for_valuation(self):
        """Return (journal_id, acc_src, acc_dest, acc_valuation)."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        accounts = product._get_product_accounts()

        journal = self.company_id.account_stock_journal_id or accounts.get('stock_journal')
        if not journal:
            journal = self.env['account.journal'].sudo().search([
                ('company_id', '=', self.company_id.id),
                ('type', '=', 'general'),
            ], limit=1)
        journal_id = journal.id if journal else False

        acc_src = self._get_counterpart_account(self.location_id, product)
        if not acc_src:
            acc_src = accounts.get('stock_input') or accounts.get('stock_variation') or self.env['account.account']

        acc_dest = self._get_counterpart_account(self.location_dest_id, product)
        if not acc_dest:
            acc_dest = accounts.get('stock_output') or accounts.get('stock_variation') or self.env['account.account']

        if self._is_in():
            acc_valuation = self.location_dest_id._get_valuation_account(product)
        else:
            acc_valuation = self.location_id._get_valuation_account(product)
        if not acc_valuation:
            acc_valuation = accounts.get('stock_valuation') or self.env['account.account']

        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_vals(
        self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost, date=None
    ):
        """Return dictionary for account.move creation with balanced lines."""
        self.ensure_one()
        credit_acc_id = credit_account_id.id if hasattr(credit_account_id, 'id') else credit_account_id
        debit_acc_id = debit_account_id.id if hasattr(debit_account_id, 'id') else debit_account_id
        j_id = journal_id.id if hasattr(journal_id, 'id') else journal_id

        abs_value = abs(cost)
        product_name = self.product_id.display_name
        ref = description or self.reference or self.description_picking or product_name
        line_name = f"{ref} - {product_name}" if product_name not in ref else ref

        svl_ids = [svl_id] if svl_id else []
        entry_date = date or fields.Date.context_today(self)

        return {
            'move_type': 'entry',
            'ref': ref,
            'journal_id': j_id,
            'date': entry_date,
            'stock_move_id': self.id,
            'stock_valuation_layer_ids': [Command.set(svl_ids)],
            'line_ids': [
                Command.create({
                    'account_id': credit_acc_id,
                    'name': line_name,
                    'debit': 0.0,
                    'credit': abs_value,
                    'product_id': self.product_id.id,
                }),
                Command.create({
                    'account_id': debit_acc_id,
                    'name': line_name,
                    'debit': abs_value,
                    'credit': 0.0,
                    'product_id': self.product_id.id,
                }),
            ],
        }

    def _account_entry_move(self, qty, description, svl_id, cost):
        """Prepare journal entry values for a valuation layer."""
        self.ensure_one()
        abs_cost = abs(cost)
        if float_is_zero(abs_cost, precision_rounding=self.company_id.currency_id.rounding):
            return []

        # Find layer date to sync entry date if needed
        svl = self.env['stock.valuation.layer'].sudo().browse(svl_id) if svl_id else None
        entry_date = fields.Date.context_today(self, svl.date) if svl and svl.date else fields.Date.context_today(self)

        if self._is_in():
            journal_id, acc_src, _, acc_valuation = self._get_accounting_data_for_valuation()
            if not journal_id or not acc_src or not acc_valuation or acc_src.id == acc_valuation.id:
                return []
            if qty >= 0:
                # Normal receipt: debit valuation, credit source/interim
                vals = self._prepare_account_move_vals(
                    acc_src.id, acc_valuation.id, journal_id, qty, description, svl_id, abs_cost, date=entry_date
                )
            else:
                # Receipt decrease adjustment: reverse entries
                vals = self._prepare_account_move_vals(
                    acc_valuation.id, acc_src.id, journal_id, qty, description, svl_id, abs_cost, date=entry_date
                )
            return [vals]

        elif self._is_out():
            journal_id, _, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if not journal_id or not acc_dest or not acc_valuation or acc_dest.id == acc_valuation.id:
                return []
            if qty <= 0:
                # Normal delivery: debit destination/COGS, credit valuation
                vals = self._prepare_account_move_vals(
                    acc_valuation.id, acc_dest.id, journal_id, qty, description, svl_id, abs_cost, date=entry_date
                )
            else:
                # Delivery decrease adjustment (return to stock): reverse entries
                vals = self._prepare_account_move_vals(
                    acc_dest.id, acc_valuation.id, journal_id, qty, description, svl_id, abs_cost, date=entry_date
                )
            return [vals]

        return []

    # -------------------------------------------------------------------------
    # Override _action_done
    # -------------------------------------------------------------------------

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)

        moves_in = self.env['stock.move']
        moves_out = self.env['stock.move']

        for move in moves:
            product = move.product_id.with_company(move.company_id)
            if not product.is_storable or product.valuation != 'real_time':
                continue

            if move._is_in() and move._should_create_in_svl():
                moves_in |= move
            elif move._is_out() and move._should_create_out_svl():
                moves_out |= move

        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        if moves_in:
            stock_valuation_layers |= moves_in._create_in_svl()
        if moves_out:
            stock_valuation_layers |= moves_out._create_out_svl()

        if stock_valuation_layers:
            stock_valuation_layers._validate_accounting_entries()

        return moves

    # -------------------------------------------------------------------------
    # Done Move Modification Engine
    # -------------------------------------------------------------------------

    def write(self, vals):
        if self.env.context.get('skip_valuation_adjust') or not any(f in vals for f in ('quantity', 'product_uom_qty')):
            return super().write(vals)

        qty_tracked_moves = self.env['stock.move']
        old_qtys = {}
        for move in self:
            if (
                move.state == 'done'
                and move.product_id.is_storable
                and move.product_id.valuation == 'real_time'
            ):
                qty_tracked_moves |= move
                old_qtys[move.id] = move.product_qty

        res = super(StockMove, self.with_context(skip_valuation_adjust=True)).write(vals)

        for move in qty_tracked_moves:
            new_qty = move.product_qty
            old_qty = old_qtys.get(move.id, new_qty)
            if old_qty != new_qty:
                move._handle_valuation_quantity_change(old_qty, new_qty)

        return res

    def _get_valuation_modification_datetime(self):
        """Return (datetime_val, date_val) for valuation modification."""
        self.ensure_one()
        company = self.company_id
        date_mode = company.svl_modification_date_mode or 'current_date'
        if date_mode == 'picking_date':
            picking = self.picking_id
            dt = (
                picking.date_done
                or picking.scheduled_date
                or self.date
                or fields.Datetime.now()
            )
            d = fields.Date.context_today(self, dt)
            return dt, d
        else:
            dt = fields.Datetime.now()
            d = fields.Date.context_today(self)
            return dt, d

    def _check_lock_date(self, check_date):
        """Verify date does not violate accounting lock dates."""
        self.ensure_one()
        company = self.company_id
        hard_lock = company.hard_lock_date
        fiscal_lock = company.fiscalyear_lock_date
        tax_lock = company.tax_lock_date

        if hard_lock and check_date <= hard_lock:
            raise UserError(_(
                "Cannot modify valuation for completed move because date %(date)s is prior to or on the hard lock date (%(lock)s).",
                date=check_date,
                lock=hard_lock,
            ))
        if fiscal_lock and check_date <= fiscal_lock:
            raise UserError(_(
                "Cannot modify valuation for completed move because date %(date)s is prior to or on the fiscal year lock date (%(lock)s).",
                date=check_date,
                lock=fiscal_lock,
            ))
        if tax_lock and check_date <= tax_lock:
            raise UserError(_(
                "Cannot modify valuation for completed move because date %(date)s is prior to or on the tax lock date (%(lock)s).",
                date=check_date,
                lock=tax_lock,
            ))

    def _handle_valuation_quantity_change(self, old_qty, new_qty):
        """Coordinate valuation adjustment when quantity on a completed move changes."""
        self.ensure_one()
        if self.env.context.get('skip_valuation_adjust'):
            return

        # 1. Permission check
        if not self.env.user.has_group('stock.group_stock_manager') and not self.env.is_superuser():
            raise UserError(_("Only Stock Managers are allowed to modify quantities on completed stock moves."))

        # 2. Scope check: disallow unsupported move types
        if getattr(self, 'is_dropship', False):
            raise UserError(_("Cannot modify valuation for completed dropship stock moves."))
        if getattr(self, 'landed_cost_ids', False):
            raise UserError(_("Cannot modify valuation for completed moves linked to landed costs."))

        # 3. Date & Lock Date Check
        datetime_val, date_val = self._get_valuation_modification_datetime()
        self._check_lock_date(date_val)

        mode = self.company_id.svl_modification_mode or 'create_diff'
        if mode == 'create_diff':
            self._process_valuation_diff_mode(old_qty, new_qty, datetime_val, date_val)
        elif mode == 'update_existing':
            self._process_valuation_update_existing_mode(old_qty, new_qty, datetime_val, date_val)

    def _get_diff_in_cost_and_value(self, delta_qty):
        """Compute unit cost and value for an incoming adjustment."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        cost_method = product.cost_method

        if cost_method == 'standard':
            unit_cost = product.standard_price
            value = self.company_id.currency_id.round(delta_qty * unit_cost)
        elif cost_method == 'average':
            unit_cost = self._get_price_unit()
            value = self.company_id.currency_id.round(delta_qty * unit_cost)
            self._recompute_product_avco_after_diff(delta_qty, value)
        elif cost_method == 'fifo':
            unit_cost = self._get_price_unit()
            value = self.company_id.currency_id.round(delta_qty * unit_cost)
        else:
            unit_cost = product.standard_price
            value = self.company_id.currency_id.round(delta_qty * unit_cost)

        return unit_cost, value

    def _get_diff_out_cost_and_value(self, delta_qty, cost_basis):
        """Compute unit cost and value for an outgoing adjustment."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        cost_method = product.cost_method

        if delta_qty > 0:
            # Additional consumption (increase in delivery)
            if cost_method == 'fifo':
                value, unit_cost = self._run_fifo(delta_qty, self.company_id)
                return unit_cost, abs(value)
            else:
                unit_cost = product.standard_price
                value = self.company_id.currency_id.round(delta_qty * unit_cost)
                return unit_cost, value
        else:
            # Quantity decrease (return to inventory)
            abs_qty = abs(delta_qty)
            if cost_basis == 'original_layer':
                if cost_method == 'fifo':
                    restored_val, unit_cost = self._restore_fifo_candidates_on_decrease(abs_qty, self.company_id)
                    return unit_cost, restored_val
                else:
                    orig_svls = self.stock_valuation_layer_ids.filtered(lambda l: l.quantity != 0)
                    unit_cost = orig_svls[-1].unit_cost if orig_svls else product.standard_price
                    value = self.company_id.currency_id.round(abs_qty * unit_cost)
                    return unit_cost, value
            else:
                unit_cost = product.standard_price
                value = self.company_id.currency_id.round(abs_qty * unit_cost)
                return unit_cost, value

    def _process_valuation_diff_mode(self, old_qty, new_qty, datetime_val, date_val):
        """Option 1: Generate compensatory SVL and Journal Entry for quantity difference."""
        self.ensure_one()
        delta_qty = new_qty - old_qty
        if float_is_zero(delta_qty, precision_rounding=self.product_uom.rounding):
            return

        cost_basis = self.company_id.svl_decrease_cost_basis or 'current_standard_price'
        new_svls = self.env['stock.valuation.layer'].sudo()

        if self._is_in():
            if delta_qty > 0:
                unit_cost, value = self._get_diff_in_cost_and_value(delta_qty)
                svl_vals = {
                    'product_id': self.product_id.id,
                    'quantity': delta_qty,
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': unit_cost,
                    'value': value,
                    'remaining_qty': delta_qty if self.product_id.cost_method == 'fifo' else 0.0,
                    'remaining_value': value if self.product_id.cost_method == 'fifo' else 0.0,
                    'stock_move_id': self.id,
                    'company_id': self.company_id.id,
                    'description': _('Adjustment (Increase): %(ref)s', ref=self.reference or self.name),
                    'date': datetime_val,
                }
            else:
                abs_qty = abs(delta_qty)
                if cost_basis == 'original_layer':
                    orig_svl = self.stock_valuation_layer_ids.filtered(lambda l: l.quantity > 0)
                    unit_cost = orig_svl[-1].unit_cost if orig_svl else self.product_id.with_company(self.company_id).standard_price
                else:
                    unit_cost = self.product_id.with_company(self.company_id).standard_price
                value = -self.company_id.currency_id.round(abs_qty * unit_cost)
                svl_vals = {
                    'product_id': self.product_id.id,
                    'quantity': -abs_qty,
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': unit_cost,
                    'value': value,
                    'remaining_qty': 0.0,
                    'remaining_value': 0.0,
                    'stock_move_id': self.id,
                    'company_id': self.company_id.id,
                    'description': _('Adjustment (Decrease): %(ref)s', ref=self.reference or self.name),
                    'date': datetime_val,
                }
                if self.product_id.cost_method == 'fifo':
                    self._run_fifo(abs_qty, self.company_id)
                elif self.product_id.cost_method == 'average':
                    self._recompute_product_avco(-abs_qty, value)

            new_svls = self.env['stock.valuation.layer'].sudo().create([svl_vals])
            new_svls._validate_accounting_entries()

        elif self._is_out():
            if delta_qty > 0:
                unit_cost, value = self._get_diff_out_cost_and_value(delta_qty, cost_basis)
                svl_vals = {
                    'product_id': self.product_id.id,
                    'quantity': -delta_qty,
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': unit_cost,
                    'value': -abs(value),
                    'remaining_qty': 0.0,
                    'remaining_value': 0.0,
                    'stock_move_id': self.id,
                    'company_id': self.company_id.id,
                    'description': _('Adjustment (Increase): %(ref)s', ref=self.reference or self.name),
                    'date': datetime_val,
                }
            else:
                abs_qty = abs(delta_qty)
                unit_cost, value = self._get_diff_out_cost_and_value(delta_qty, cost_basis)
                svl_vals = {
                    'product_id': self.product_id.id,
                    'quantity': abs_qty,
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': unit_cost,
                    'value': abs(value),
                    'remaining_qty': 0.0,
                    'remaining_value': 0.0,
                    'stock_move_id': self.id,
                    'company_id': self.company_id.id,
                    'description': _('Adjustment (Decrease): %(ref)s', ref=self.reference or self.name),
                    'date': datetime_val,
                }

            new_svls = self.env['stock.valuation.layer'].sudo().create([svl_vals])
            new_svls._validate_accounting_entries()

        # Synchronize date if picking_date is configured
        if self.company_id.svl_modification_date_mode == 'picking_date':
            self.with_context(skip_valuation_adjust=True).write({'date': datetime_val})
            self.move_line_ids.with_context(skip_valuation_adjust=True).write({'date': datetime_val})

        # Post chatter notification
        if self.picking_id:
            jes = new_svls.account_move_id
            self.picking_id.message_post(body=_(
                "Valuation Adjustment for move %(move)s (%(prod)s): quantity changed from %(old)s to %(new)s %(uom)s.<br/>"
                "SVLs created: %(svls)s.<br/>"
                "Journal entries created: %(jes)s.",
                move=self.reference or self.name,
                prod=self.product_id.display_name,
                old=old_qty,
                new=new_qty,
                uom=self.product_uom.name,
                svls=", ".join(map(str, new_svls.ids)),
                jes=", ".join(jes.mapped('name')) if jes else "None",
            ))

    def _process_valuation_update_existing_mode(self, old_qty, new_qty, datetime_val, date_val):
        """Option 2: Update existing valuation layer and modify original journal entry."""
        self.ensure_one()
        delta_qty = new_qty - old_qty
        if float_is_zero(delta_qty, precision_rounding=self.product_uom.rounding):
            return

        svls = self.stock_valuation_layer_ids.filtered(lambda l: l.quantity != 0)
        if not svls:
            # Fallback to diff mode if no existing layer exists
            return self._process_valuation_diff_mode(old_qty, new_qty, datetime_val, date_val)

        if self._is_in():
            orig_svl = svls[0]
            unit_cost = orig_svl.unit_cost
            old_val = orig_svl.value
            old_l_qty = orig_svl.quantity
            new_l_qty = new_qty
            new_val = self.company_id.currency_id.round(new_l_qty * unit_cost)

            svl_update_vals = {
                'quantity': new_l_qty,
                'value': new_val,
                'date': datetime_val,
            }
            if self.product_id.cost_method == 'fifo':
                new_rem = max(0.0, orig_svl.remaining_qty + delta_qty)
                svl_update_vals['remaining_qty'] = new_rem
                svl_update_vals['remaining_value'] = self.company_id.currency_id.round(new_rem * unit_cost)

            orig_svl.sudo().write(svl_update_vals)

            if self.product_id.cost_method == 'average':
                self._recompute_product_avco_after_adjustment(old_val, new_val, old_l_qty, new_l_qty)

            self._update_existing_account_moves(orig_svl, date_val)

        elif self._is_out():
            orig_svl = svls[0]
            cost_method = self.product_id.cost_method
            unit_cost = orig_svl.unit_cost
            old_val = orig_svl.value

            if cost_method == 'fifo':
                if delta_qty > 0:
                    diff_val, _ = self._run_fifo(delta_qty, self.company_id)
                    new_val = old_val + diff_val
                else:
                    restored_val, _ = self._restore_fifo_candidates_on_decrease(abs(delta_qty), self.company_id)
                    new_val = old_val + restored_val
                new_l_qty = -new_qty
                unit_cost = abs(new_val / new_l_qty) if new_l_qty else orig_svl.unit_cost
            else:
                new_l_qty = -new_qty
                new_val = -self.company_id.currency_id.round(new_qty * unit_cost)

            orig_svl.sudo().write({
                'quantity': new_l_qty,
                'value': new_val,
                'unit_cost': unit_cost,
                'date': datetime_val,
            })
            self._update_existing_account_moves(orig_svl, date_val)

        # Synchronize move dates
        if self.company_id.svl_modification_date_mode == 'picking_date':
            self.with_context(skip_valuation_adjust=True).write({'date': datetime_val})
            self.move_line_ids.with_context(skip_valuation_adjust=True).write({'date': datetime_val})

        if self.picking_id:
            self.picking_id.message_post(body=_(
                "Valuation Update for move %(move)s: quantity updated from %(old)s to %(new)s %(uom)s.<br/>"
                "Layer %(svl)s updated to value %(val)s.",
                move=self.reference or self.name,
                old=old_qty,
                new=new_qty,
                uom=self.product_uom.name,
                svl=svls[0].id,
                val=svls[0].value,
            ))

    def _update_existing_account_moves(self, svl, date_val):
        """Update and repost the existing Journal Entry linked to the valuation layer."""
        account_move = svl.account_move_id
        if not account_move:
            return

        if getattr(account_move.journal_id, 'restrict_mode_hash_table', False):
            raise UserError(_(
                "Cannot modify journal entry %(name)s because journal %(journal)s enforces hash restrictions.",
                name=account_move.name,
                journal=account_move.journal_id.name,
            ))
        if any(line.reconciled for line in account_move.line_ids):
            raise UserError(_(
                "Cannot modify journal entry %(name)s because its accounting lines are reconciled.",
                name=account_move.name,
            ))

        account_move.button_draft()
        if account_move.date != date_val:
            account_move.name = False
            account_move.date = date_val

        abs_val = abs(svl.value)
        for line in account_move.line_ids:
            if line.debit > 0:
                line.debit = abs_val
            elif line.credit > 0:
                line.credit = abs_val

        account_move.action_post()
        account_move.message_post(body=_(
            "Journal entry amount updated to %(val)s following stock move quantity adjustment.",
            val=abs_val,
        ))
