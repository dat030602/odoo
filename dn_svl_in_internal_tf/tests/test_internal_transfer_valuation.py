# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

        # Valuation group
        cls.valuation_group = cls.env.ref('dn_svl_in_internal_tf.group_internal_transfer_valuation')

        # Test user with stock user and valuation group
        cls.test_user = cls.env['res.users'].create({
            'name': 'Valuation Test User',
            'login': 'val_test_user',
            'email': 'val_test_user@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
                cls.valuation_group.id,
            ])],
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
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

    def _create_and_confirm_move(self, product, src_loc, dest_loc, qty=10.0):
        """Helper to create and confirm a stock move."""
        move = self.env['stock.move'].create({
            'description_picking': f'Move {product.name}',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty,
            'location_id': src_loc.id,
            'location_dest_id': dest_loc.id,
            'company_id': self.company.id,
        })
        move._action_confirm()
        return move

    def test_01_res_config_settings(self):
        """Test configuration setting to enable / disable internal transfer valuation."""
        settings = self.env['res.config.settings'].create({
            'group_internal_transfer_valuation': True,
        })
        settings.execute()
        self.assertTrue(
            self.test_user.has_group('dn_svl_in_internal_tf.group_internal_transfer_valuation'),
            "Setting should enable group_internal_transfer_valuation."
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

        # Without group
        self.test_user.group_ids -= self.valuation_group
        self.assertFalse(
            move_internal.with_user(self.test_user)._is_internal_transfer(),
            "Move must not qualify if user does not have the valuation group."
        )
        self.test_user.group_ids |= self.valuation_group

    def test_03_internal_transfer_accounts_resolution(self):
        """Test _get_internal_transfer_accounts helper."""
        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, 10.0
        )
        credit_acc, debit_acc = move._get_internal_transfer_accounts()
        self.assertEqual(credit_acc, self.account_wh1, "Credit account should be source location account.")
        self.assertEqual(debit_acc, self.account_wh2, "Debit account should be destination location account.")

    def test_04_skip_account_move_when_accounts_identical(self):
        """Verify journal entry creation is skipped when source and dest accounts are identical."""
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
        self.assertFalse(
            svls.mapped('account_move_id'),
            "No journal entry should be created when source and destination accounts are identical."
        )

    def test_05_full_internal_transfer_flow_with_different_accounts(self):
        """Verify full flow: Move done creates 2 SVL records and a posted Journal Entry."""
        qty = 4.0
        unit_cost = self.product_real_time.standard_price  # 50.0
        expected_total_value = qty * unit_cost  # 200.0

        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, qty
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

        # Check Account Move
        account_move = svl_in.account_move_id
        self.assertTrue(account_move, "SVL record must be linked to a journal entry.")
        self.assertEqual(svl_out.account_move_id, account_move, "Both SVLs must link to the same entry.")
        self.assertEqual(account_move.state, 'posted', "Journal entry must be posted.")

        # Check Journal Entry Lines
        lines = account_move.line_ids
        self.assertEqual(len(lines), 2, "Journal entry must have exactly 2 lines (debit & credit).")

        credit_line = lines.filtered(lambda l: l.credit > 0)
        debit_line = lines.filtered(lambda l: l.debit > 0)

        self.assertEqual(credit_line.account_id, self.account_wh1, "Credit line must use source warehouse account.")
        self.assertEqual(credit_line.credit, expected_total_value)

        self.assertEqual(debit_line.account_id, self.account_wh2, "Debit line must use dest warehouse account.")
        self.assertEqual(debit_line.debit, expected_total_value)

    def test_06_skip_when_feature_disabled(self):
        """Verify no SVL or journal entry is created when group is disabled."""
        self.test_user.group_ids -= self.valuation_group

        move = self._create_and_confirm_move(
            self.product_real_time, self.loc_wh1, self.loc_wh2, 5.0
        )
        move.quantity = 5.0
        move.picked = True
        move.with_user(self.test_user)._action_done()

        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertFalse(svls, "No SVL records should be created when feature is disabled.")
        self.test_user.group_ids |= self.valuation_group
