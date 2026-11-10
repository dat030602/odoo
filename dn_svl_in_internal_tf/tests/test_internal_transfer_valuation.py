# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestInternalTransferValuation(TransactionCase):
    """Test suite for Stock Valuation Layer & Journal Entry creation on internal transfers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Ensure currency
        cls.currency = cls.company.currency_id

        # Create valuation accounts
        cls.account_wh1 = cls.env['account.account'].create({
            'name': 'Warehouse 1 Valuation Account',
            'code': '1010201',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_wh2 = cls.env['account.account'].create({
            'name': 'Warehouse 2 Valuation Account',
            'code': '1010202',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_transit = cls.env['account.account'].create({
            'name': 'Stock Transit Account',
            'code': '1010203',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_wh1.account_stock_variation_id = cls.account_transit.id
        cls.account_wh2.account_stock_variation_id = cls.account_transit.id

        # Ensure stock journal exists
        cls.stock_journal = cls.company.account_stock_journal_id
        if not cls.stock_journal:
            cls.stock_journal = cls.env['account.journal'].create({
                'name': 'Stock Journal Test',
                'type': 'general',
                'code': 'STKJ',
                'company_id': cls.company.id,
            })
            cls.company.account_stock_journal_id = cls.stock_journal.id

        # Valuation move type configuration for internal transfer
        cls.type_internal = cls.env.ref('dn_svl_in_internal_tf.move_type_internal_transfer')
        cls.company.write({
            'auto_svl_move_type_ids': [Command.set([cls.type_internal.id])],
            'auto_je_move_type_ids': [Command.set([cls.type_internal.id])],
        })

        # Test user with strictly stock user rights (no accounting rights)
        cls.test_user = cls.env['res.users'].create({
            'name': 'Valuation Test User',
            'login': 'val_test_user',
            'email': 'val_test_user@example.com',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
            ])],
            'company_id': cls.company.id,
            'company_ids': [Command.set([cls.company.id])],
        })

        # Product categories
        cls.category_real_time = cls.env['product.category'].create({
            'name': 'Real-Time Category',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.account_wh1.id,
        })
        cls.category_manual = cls.env['product.category'].create({
            'name': 'Manual Category',
            'property_valuation': 'periodic',
        })

        # Products
        cls.product_real_time = cls.env['product.product'].create({
            'name': 'Real-time Valued Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category_real_time.id,
            'standard_price': 50.0,
            'use_location_valuation_account': True,
        })
        cls.product_manual = cls.env['product.product'].create({
            'name': 'Manual Valued Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category_manual.id,
            'standard_price': 30.0,
        })

        # Locations
        cls.loc_wh1 = cls.env['stock.location'].create({
            'name': 'WH1 Stock',
            'usage': 'internal',
            'dn_valuation_account_id': cls.account_wh1.id,
        })
        cls.loc_wh2 = cls.env['stock.location'].create({
            'name': 'WH2 Stock',
            'usage': 'internal',
            'dn_valuation_account_id': cls.account_wh2.id,
        })
        cls.customer_loc = cls.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        if not cls.customer_loc:
            cls.customer_loc = cls.env['stock.location'].create({
                'name': 'Customers Test Location',
                'usage': 'customer',
            })

    def _create_and_confirm_move(self, product, src_loc, dest_loc, qty=10.0, picking=None):
        """Helper to create and confirm a stock move."""
        vals = {
            'description_picking': f'Move {product.name}',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty,
            'location_id': src_loc.id,
            'location_dest_id': dest_loc.id,
            'company_id': self.company.id,
        }
        if picking:
            vals['picking_id'] = picking.id
        move = self.env['stock.move'].create(vals)
        move._action_confirm()
        return move

    def test_01_res_config_settings(self):
        """Test configuration setting to enable / disable move types for SVL and Journal Entries."""
        settings = self.env['res.config.settings'].create({
            'auto_svl_move_type_ids': [Command.set([self.type_internal.id])],
            'auto_je_move_type_ids': [Command.set([self.type_internal.id])],
        })
        settings.execute()
        self.assertIn(
            self.type_internal,
            self.company.auto_svl_move_type_ids,
            "Setting should enable internal transfer in auto_svl_move_type_ids."
        )
        self.assertIn(
            self.type_internal,
            self.company.auto_je_move_type_ids,
            "Setting should enable internal transfer in auto_je_move_type_ids."
        )

    def test_02_is_internal_transfer_conditions(self):
        """Test all guard conditions of _is_internal_transfer."""
        move_internal = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, 5.0
        )
        self.assertTrue(
            move_internal.with_user(self.test_user)._is_internal_transfer(),
            "Move between internal locations with real_time product must qualify."
        )

        # Non-internal destination
        move_to_customer = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.customer_loc, 5.0
        )
        self.assertFalse(
            move_to_customer.with_user(self.test_user)._is_internal_transfer(),
            "Move to non-internal location must not qualify."
        )

        # Manual valuation product
        move_manual = self._create_and_confirm_move(
            self.product_manual, self.loc_wh1, self.loc_wh2, 5.0
        )
        self.assertFalse(
            move_manual.with_user(self.test_user)._is_internal_transfer(),
            "Move with manual valuation product must not qualify."
        )

        # Without internal_transfer move type configured
        self.company.write({
            'auto_je_move_type_ids': [Command.clear()],
            'auto_svl_move_type_ids': [Command.clear()],
        })
        self.assertFalse(
            move_internal.with_user(self.test_user)._is_internal_transfer(),
            "Move must not qualify if internal transfer is not configured in auto_svl_move_type_ids."
        )
        self.company.write({
            'auto_svl_move_type_ids': [Command.set([self.type_internal.id])],
            'auto_je_move_type_ids': [Command.set([self.type_internal.id])],
        })

    def test_03_internal_transfer_accounts_resolution(self):
        """Test _get_internal_transfer_accounts helper."""
        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, 10.0
        )
        credit_acc, debit_acc = move._get_internal_transfer_accounts()
        self.assertEqual(credit_acc, self.account_wh1, "Credit account should be source location account.")
        self.assertEqual(debit_acc, self.account_wh2, "Debit account should be destination location account.")

    def test_04_create_account_moves_when_accounts_identical(self):
        """Verify journal entries are created even when source and dest locations share the same valuation account."""
        # Transfer from WH1 to WH1 (same account)
        loc_wh1_shelf = self.env['stock.location'].create({
            'name': 'WH1 Shelf',
            'usage': 'internal',
            'location_id': self.loc_wh1.id,
        })
        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, loc_wh1_shelf, 5.0
        )
        move.quantity = 5.0
        move.picked = True
        move.with_user(self.test_user)._action_done()

        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertEqual(len(svls), 2, "SVL records should still be created for traceability.")
        account_moves = svls.mapped('account_move_id')
        self.assertEqual(
            len(account_moves), 2,
            "Two journal entries should still be created via transit account even when source and destination accounts are identical."
        )

    def test_05_full_internal_transfer_flow_with_different_accounts(self):
        """Verify full flow: Move done creates 2 SVL records and 2 posted Journal Entries."""
        qty = 4.0
        unit_cost = self.product_real_time.standard_price  # 50.0
        expected_total_value = qty * unit_cost  # 200.0

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].create({
                'name': 'Internal Transfers Test 05',
                'code': 'internal',
                'sequence_code': 'INT05',
                'company_id': self.company.id,
            })

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.loc_wh1.id,
            'location_dest_id': self.loc_wh2.id,
            'company_id': self.company.id,
        })

        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, qty, picking=picking
        )
        move.quantity = qty
        move.picked = True
        move.with_user(self.test_user)._action_done()

        # Check SVL records
        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertEqual(len(svls), 2, "Should create exactly 2 SVL records (OUT and IN).")

        svl_out = svls.filtered(lambda s: s.quantity < 0)
        svl_in = svls.filtered(lambda s: s.quantity > 0)

        self.assertEqual(len(svl_out), 1, "Must have exactly 1 negative SVL (source OUT).")
        self.assertEqual(len(svl_in), 1, "Must have exactly 1 positive SVL (dest IN).")

        self.assertEqual(svl_out.quantity, -qty)
        self.assertEqual(svl_out.value, -expected_total_value)
        self.assertEqual(svl_out.unit_cost, unit_cost)

        self.assertEqual(svl_in.quantity, qty)
        self.assertEqual(svl_in.value, expected_total_value)
        self.assertEqual(svl_in.unit_cost, unit_cost)

        # Check Account Moves
        account_move_out = svl_out.account_move_id
        account_move_in = svl_in.account_move_id
        self.assertTrue(account_move_out, "SVL OUT must be linked to a journal entry.")
        self.assertTrue(account_move_in, "SVL IN must be linked to a journal entry.")
        self.assertNotEqual(account_move_out, account_move_in, "SVL OUT and SVL IN must have distinct journal entries.")
        self.assertEqual(account_move_out.state, 'posted', "OUT journal entry must be posted.")
        self.assertEqual(account_move_in.state, 'posted', "IN journal entry must be posted.")

        # Check Account Move SVL link and counts
        self.assertEqual(account_move_out.stock_valuation_layer_ids, svl_out)
        self.assertEqual(account_move_in.stock_valuation_layer_ids, svl_in)
        self.assertEqual(account_move_out.dn_svl_count, 1, "OUT journal entry SVL count must be 1.")
        self.assertEqual(account_move_in.dn_svl_count, 1, "IN journal entry SVL count must be 1.")

        # Check SVL action_dn_view_account_move
        self.assertEqual(svl_out.action_dn_view_account_move()['res_id'], account_move_out.id)
        self.assertEqual(svl_in.action_dn_view_account_move()['res_id'], account_move_in.id)

        # Check Account Move navigation actions
        action_svl = account_move_out.action_dn_view_svl()
        self.assertEqual(action_svl['res_model'], 'stock.valuation.layer')
        self.assertEqual(action_svl['domain'], [('account_move_id', '=', account_move_out.id)])

        action_sm = account_move_out.action_dn_view_stock_moves()
        self.assertEqual(action_sm['res_model'], 'stock.move')
        self.assertEqual(action_sm['domain'], [('account_move_id', '=', account_move_out.id)])

        transit_account = move._get_interim_transit_account()

        # Check OUT Journal Entry Lines (Credit WH1, Debit Transit)
        lines_out = account_move_out.line_ids
        self.assertEqual(len(lines_out), 2, "OUT journal entry must have exactly 2 lines.")
        credit_line_out = lines_out.filtered(lambda l: l.credit > 0)
        debit_line_out = lines_out.filtered(lambda l: l.debit > 0)
        self.assertEqual(credit_line_out.account_id, self.account_wh1, "Credit line must use source warehouse account.")
        self.assertEqual(credit_line_out.credit, expected_total_value)
        self.assertEqual(debit_line_out.account_id, transit_account, "Debit line must use interim transit account.")
        self.assertEqual(debit_line_out.debit, expected_total_value)

        # Check IN Journal Entry Lines (Debit WH2, Credit Transit)
        lines_in = account_move_in.line_ids
        self.assertEqual(len(lines_in), 2, "IN journal entry must have exactly 2 lines.")
        debit_line_in = lines_in.filtered(lambda l: l.debit > 0)
        credit_line_in = lines_in.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line_in.account_id, self.account_wh2, "Debit line must use dest warehouse account.")
        self.assertEqual(debit_line_in.debit, expected_total_value)
        self.assertEqual(credit_line_in.account_id, transit_account, "Credit line must use interim transit account.")
        self.assertEqual(credit_line_in.credit, expected_total_value)

        # Transit account balances to zero
        transit_lines = (lines_out | lines_in).filtered(lambda l: l.account_id == transit_account)
        total_transit_debit = sum(transit_lines.mapped('debit'))
        total_transit_credit = sum(transit_lines.mapped('credit'))
        self.assertEqual(total_transit_debit, total_transit_credit, "Transit account debit must equal credit (balance to zero).")
        self.assertEqual(total_transit_debit - total_transit_credit, 0.0, "Transit account net balance must be zero.")

        # Verify picking journal entry count
        self.assertEqual(picking.dn_account_move_count, 2, "Picking must count exactly 2 journal entries.")

    def test_06_skip_when_feature_disabled(self):
        """Verify no SVL or journal entry is created when move type is disabled."""
        self.company.write({
            'auto_je_move_type_ids': [Command.clear()],
            'auto_svl_move_type_ids': [Command.clear()],
        })

        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, 5.0
        )
        move.quantity = 5.0
        move.picked = True
        move.with_user(self.test_user)._action_done()

        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertFalse(svls, "No SVL records should be created when feature is disabled.")
        self.company.write({
            'auto_svl_move_type_ids': [Command.set([self.type_internal.id])],
            'auto_je_move_type_ids': [Command.set([self.type_internal.id])],
        })

    def test_07_picking_smart_buttons_and_navigation(self):
        """Test picking smart buttons, counters, and act_window actions."""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].create({
                'name': 'Internal Transfers Test',
                'code': 'internal',
                'sequence_code': 'INT',
                'company_id': self.company.id,
            })

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.loc_wh1.id,
            'location_dest_id': self.loc_wh2.id,
            'company_id': self.company.id,
        })
        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, 6.0, picking=picking
        )
        move.quantity = 6.0
        move.picked = True
        move.with_user(self.test_user)._action_done()

        self.assertEqual(picking.dn_account_move_count, 2, "Picking should count 2 journal entries.")
        self.assertEqual(picking.dn_svl_count, 2, "Picking should count 2 SVL records.")

        # Test view account moves returns domain with both account moves
        account_moves = picking.move_ids.stock_valuation_layer_ids.account_move_id
        action_am = picking.action_dn_view_account_moves()
        self.assertEqual(action_am['res_model'], 'account.move')
        self.assertEqual(set(action_am['domain'][0][2]), set(account_moves.ids))

        # Test SVL action returns list,form view
        action_svl = picking.action_dn_view_svl()
        self.assertEqual(action_svl['res_model'], 'stock.valuation.layer')
        self.assertEqual(action_svl['view_mode'], 'list,form')
        svl_ids = move.stock_valuation_layer_ids.ids
        self.assertEqual(set(action_svl['domain'][0][2]), set(svl_ids))

        # Test SVL action without account move returns empty dict
        svl_no_am = self.env['stock.valuation.layer'].create({
            'product_id': self.product_real_time.id,
            'quantity': 1.0,
            'unit_cost': 50.0,
            'value': 50.0,
            'company_id': self.company.id,
        })
        self.assertEqual(svl_no_am.action_dn_view_account_move(), {})

    def test_08_stock_user_without_accounting_rights_can_generate_svl_and_je(self):
        """Verify a user with strictly only Stock User rights (no accounting groups)
        can validate an internal transfer and successfully generate SVLs and posted Journal Entry.
        """
        # Create pure stock user
        stock_user = self.env['res.users'].create({
            'name': 'Pure Stock User',
            'login': 'pure_stock_user',
            'email': 'pure_stock_user@example.com',
            'group_ids': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('stock.group_stock_user').id,
            ])],
            'company_id': self.company.id,
            'company_ids': [Command.set([self.company.id])],
        })

        # Explicitly verify user does NOT belong to any accounting groups
        accounting_category = self.env.ref('base.module_category_accounting_accounting', raise_if_not_found=False)
        if accounting_category:
            user_accounting_groups = stock_user.group_ids.filtered(
                lambda g: g.category_id == accounting_category
            )
            self.assertFalse(user_accounting_groups, "Test user must have NO accounting groups.")

        qty = 3.0
        unit_cost = self.product_real_time.standard_price  # 50.0
        expected_total_value = qty * unit_cost

        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, qty
        )
        move.quantity = qty
        move.picked = True

        # Pure stock user validates the transfer
        move.with_user(stock_user)._action_done()

        # Check 2 SVLs created
        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertEqual(len(svls), 2, "Should create 2 SVLs.")

        svl_out = svls.filtered(lambda s: s.quantity < 0)
        svl_in = svls.filtered(lambda s: s.quantity > 0)

        # Check both OUT and IN journal entries exist, are distinct, and posted
        account_move_out = svl_out.account_move_id
        account_move_in = svl_in.account_move_id
        self.assertTrue(account_move_out, "OUT Journal Entry must be created.")
        self.assertTrue(account_move_in, "IN Journal Entry must be created.")
        self.assertNotEqual(account_move_out, account_move_in, "Both journal entries must be distinct.")
        self.assertEqual(account_move_out.state, 'posted', "OUT journal entry must be posted.")
        self.assertEqual(account_move_in.state, 'posted', "IN journal entry must be posted.")

        transit_account = move._get_interim_transit_account()

        # Check OUT lines balance: Credit WH1, Debit Transit
        self.assertEqual(len(account_move_out.line_ids), 2, "OUT journal entry must have 2 lines.")
        credit_out = account_move_out.line_ids.filtered(lambda l: l.credit > 0)
        debit_out = account_move_out.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(credit_out.account_id, self.account_wh1)
        self.assertEqual(credit_out.credit, expected_total_value)
        self.assertEqual(debit_out.account_id, transit_account)
        self.assertEqual(debit_out.debit, expected_total_value)

        # Check IN lines balance: Credit Transit, Debit WH2
        self.assertEqual(len(account_move_in.line_ids), 2, "IN journal entry must have 2 lines.")
        credit_in = account_move_in.line_ids.filtered(lambda l: l.credit > 0)
        debit_in = account_move_in.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(credit_in.account_id, transit_account)
        self.assertEqual(credit_in.credit, expected_total_value)
        self.assertEqual(debit_in.account_id, self.account_wh2)
        self.assertEqual(debit_in.debit, expected_total_value)
