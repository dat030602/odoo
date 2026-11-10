# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDoneMoveModification(TransactionCase):
    """Test suite for completed (done) stock move quantity modifications."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.svl_modification_mode = 'create_diff'
        cls.company.svl_modification_date_mode = 'current_date'
        cls.company.svl_decrease_cost_basis = 'current_standard_price'

        # Accounts
        cls.account_stock = cls.env['account.account'].create({
            'name': 'Stock Valuation Move Mod',
            'code': '1010321',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_interim = cls.env['account.account'].create({
            'name': 'Stock Interim Move Mod',
            'code': '1010322',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })

        # Journal
        cls.stock_journal = cls.company.account_stock_journal_id
        if not cls.stock_journal:
            cls.stock_journal = cls.env['account.journal'].create({
                'name': 'Stock Journal Mod Test',
                'type': 'general',
                'code': 'STKMD',
                'company_id': cls.company.id,
            })
            cls.company.account_stock_journal_id = cls.stock_journal.id

        # Category
        cls.category = cls.env['product.category'].create({
            'name': 'Move Mod Test Category',
            'property_cost_method': 'standard',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.account_stock.id,
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Move Mod Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
            'standard_price': 50.0,
            'use_location_valuation_account': True,
        })

        # Locations
        cls.loc_stock = cls.env['stock.location'].create({
            'name': 'Stock Mod Location',
            'usage': 'internal',
            'dn_valuation_account_id': cls.account_stock.id,
        })
        cls.loc_supplier = cls.env['stock.location'].create({
            'name': 'Supplier Mod Location',
            'usage': 'supplier',
            'dn_valuation_account_id': cls.account_interim.id,
        })
        cls.loc_customer = cls.env['stock.location'].create({
            'name': 'Customer Mod Location',
            'usage': 'customer',
            'dn_valuation_account_id': cls.account_interim.id,
        })

        # Stock Manager user
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Stock Manager User Mod Test',
            'login': 'stock_manager_mod_test',
            'email': 'stock_manager_mod_test@example.com',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_manager').id,
            ])],
            'company_id': cls.company.id,
            'company_ids': [Command.set([cls.company.id])],
        })

        # Non-manager user
        cls.regular_user = cls.env['res.users'].create({
            'name': 'Regular User Mod Test',
            'login': 'regular_user_mod_test',
            'email': 'regular_user_mod_test@example.com',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
            ])],
            'company_id': cls.company.id,
            'company_ids': [Command.set([cls.company.id])],
        })

    def _create_done_receipt_move(self, qty=10.0):
        """Helper to create a done receipt move with initial SVL and JE."""
        move = self.env['stock.move'].create({
            'name': 'Done Receipt Test',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': qty,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
            'state': 'done',
        })
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'quantity': qty,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
            'picked': True,
        })
        svl = move._create_in_svl(forced_quantity=qty)
        svl._validate_accounting_entries()
        return move, svl

    def test_01_diff_mode_increase(self):
        """Test create_diff mode creates adjustment SVL and JE on increase."""
        self.company.svl_modification_mode = 'create_diff'
        move, initial_svl = self._create_done_receipt_move(10.0)

        # Increase quantity from 10 to 15
        move.with_user(self.manager_user)._handle_valuation_quantity_change(10.0, 15.0)

        svls = move.stock_valuation_layer_ids.sorted('id')
        self.assertEqual(len(svls), 2, "An adjustment SVL should be created.")
        adj_svl = svls[-1]
        self.assertEqual(adj_svl.quantity, 5.0)
        self.assertEqual(adj_svl.value, 250.0)
        self.assertTrue(adj_svl.account_move_id, "Adjustment SVL must have a linked journal entry.")
        self.assertEqual(adj_svl.account_move_id.amount_total, 250.0)

    def test_02_diff_mode_decrease(self):
        """Test create_diff mode creates adjustment SVL and JE on decrease."""
        self.company.svl_modification_mode = 'create_diff'
        move, initial_svl = self._create_done_receipt_move(10.0)

        # Decrease quantity from 10 to 8
        move.with_user(self.manager_user)._handle_valuation_quantity_change(10.0, 8.0)

        svls = move.stock_valuation_layer_ids.sorted('id')
        self.assertEqual(len(svls), 2)
        adj_svl = svls[-1]
        self.assertEqual(adj_svl.quantity, -2.0)
        self.assertEqual(adj_svl.value, -100.0)
        self.assertTrue(adj_svl.account_move_id)
        self.assertEqual(adj_svl.account_move_id.amount_total, 100.0)

    def test_03_update_existing_mode(self):
        """Test update_existing mode updates original SVL and reposts JE."""
        self.company.svl_modification_mode = 'update_existing'
        move, initial_svl = self._create_done_receipt_move(10.0)
        initial_je = initial_svl.account_move_id
        self.assertTrue(initial_je)
        self.assertEqual(initial_je.amount_total, 500.0)

        # Update quantity from 10 to 14
        move.with_user(self.manager_user)._handle_valuation_quantity_change(10.0, 14.0)

        svls = move.stock_valuation_layer_ids
        self.assertEqual(len(svls), 1, "No new SVL should be created in update_existing mode.")
        self.assertEqual(initial_svl.quantity, 14.0)
        self.assertEqual(initial_svl.value, 700.0)

        # Journal Entry check
        self.assertEqual(initial_je.state, 'posted')
        self.assertEqual(initial_je.amount_total, 700.0)

    def test_04_lock_date_protection(self):
        """Test modifying valuation on or before lock date raises UserError."""
        move, initial_svl = self._create_done_receipt_move(10.0)
        today = fields.Date.context_today(move)

        # Set hard lock date to today
        self.company.hard_lock_date = today

        with self.assertRaises(UserError):
            move.with_user(self.manager_user)._handle_valuation_quantity_change(10.0, 12.0)

    def test_05_permission_check(self):
        """Test non-manager cannot modify valuation of completed move."""
        move, initial_svl = self._create_done_receipt_move(10.0)

        with self.assertRaises(UserError):
            move.with_user(self.regular_user)._handle_valuation_quantity_change(10.0, 12.0)

    def test_06_date_mode_picking_date(self):
        """Test picking_date mode sets modification date to picking date_done."""
        self.company.svl_modification_mode = 'create_diff'
        self.company.svl_modification_date_mode = 'picking_date'

        past_date = fields.Datetime.now() - timedelta(days=5)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.picking.type'].search([], limit=1).id,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
            'date_done': past_date,
        })
        move = self.env['stock.move'].create({
            'name': 'Picking Date Move Test',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 10.0,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
            'picking_id': picking.id,
            'state': 'done',
        })
        initial_svl = move._create_in_svl(forced_quantity=10.0)
        initial_svl._validate_accounting_entries()

        # Adjust quantity
        move.with_user(self.manager_user)._handle_valuation_quantity_change(10.0, 12.0)

        adj_svl = (move.stock_valuation_layer_ids - initial_svl)[0]
        self.assertEqual(adj_svl.date, past_date)
        expected_date = fields.Date.context_today(move, past_date)
        self.assertEqual(adj_svl.account_move_id.date, expected_date)
