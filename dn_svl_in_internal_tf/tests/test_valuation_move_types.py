# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestValuationMoveTypes(TransactionCase):
    """Test suite for configurable Stock Valuation Move Types (receipt, delivery, internal transfer)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Ensure currency
        cls.currency = cls.company.currency_id

        # Move type records
        cls.type_delivery = cls.env.ref('dn_svl_in_internal_tf.move_type_delivery')
        cls.type_receipt = cls.env.ref('dn_svl_in_internal_tf.move_type_receipt')
        cls.type_internal = cls.env.ref('dn_svl_in_internal_tf.move_type_internal_transfer')

        # Create valuation and variation accounts
        cls.account_stock = cls.env['account.account'].create({
            'name': 'Stock Valuation Account',
            'code': '1010301',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_interim = cls.env['account.account'].create({
            'name': 'Stock Interim / Variation Account',
            'code': '1010302',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_wh2 = cls.env['account.account'].create({
            'name': 'Warehouse 2 Stock Account',
            'code': '1010303',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_stock.account_stock_variation_id = cls.account_interim.id
        cls.account_wh2.account_stock_variation_id = cls.account_interim.id

        # Ensure stock journal exists
        cls.stock_journal = cls.company.account_stock_journal_id
        if not cls.stock_journal:
            cls.stock_journal = cls.env['account.journal'].create({
                'name': 'Stock Journal Valuation Types Test',
                'type': 'general',
                'code': 'STKJV',
                'company_id': cls.company.id,
            })
            cls.company.account_stock_journal_id = cls.stock_journal.id

        # Product category with automated valuation
        cls.category = cls.env['product.category'].create({
            'name': 'Configurable Valuation Category',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.account_stock.id,
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Valued Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
            'standard_price': 40.0,
            'use_location_valuation_account': True,
        })

        # Locations
        cls.loc_stock = cls.env['stock.location'].create({
            'name': 'Main Stock Location',
            'usage': 'internal',
            'dn_valuation_account_id': cls.account_stock.id,
        })
        cls.loc_wh2 = cls.env['stock.location'].create({
            'name': 'WH2 Stock Location',
            'usage': 'internal',
            'dn_valuation_account_id': cls.account_wh2.id,
        })
        cls.loc_supplier = cls.env['stock.location'].create({
            'name': 'Supplier Location',
            'usage': 'supplier',
            'dn_valuation_account_id': cls.account_interim.id,
        })
        cls.loc_customer = cls.env['stock.location'].create({
            'name': 'Customer Location',
            'usage': 'customer',
            'dn_valuation_account_id': cls.account_interim.id,
        })

        # Picking types
        cls.picking_type_in = cls.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        if not cls.picking_type_in:
            cls.picking_type_in = cls.env['stock.picking.type'].create({
                'name': 'Receipts Test',
                'code': 'incoming',
                'sequence_code': 'IN',
                'company_id': cls.company.id,
            })

        cls.picking_type_out = cls.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        if not cls.picking_type_out:
            cls.picking_type_out = cls.env['stock.picking.type'].create({
                'name': 'Deliveries Test',
                'code': 'outgoing',
                'sequence_code': 'OUT',
                'company_id': cls.company.id,
            })

    def _create_and_confirm_move(self, product, src_loc, dest_loc, qty=5.0, picking=None):
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

    def test_constraint_je_requires_svl(self):
        """Attempting to enable Journal Entry without enabling SVL raises ValidationError."""
        # Clean company configuration first
        self.company.write({
            'auto_svl_move_type_ids': [Command.clear()],
            'auto_je_move_type_ids': [Command.clear()],
        })

        # Attempt to enable JE without SVL
        with self.assertRaises(ValidationError):
            self.company.write({
                'auto_svl_move_type_ids': [Command.clear()],
                'auto_je_move_type_ids': [Command.set([self.type_receipt.id])],
            })

        # Enabling both SVL and JE succeeds
        self.company.write({
            'auto_svl_move_type_ids': [Command.set([self.type_receipt.id])],
            'auto_je_move_type_ids': [Command.set([self.type_receipt.id])],
        })
        self.assertIn(self.type_receipt, self.company.auto_svl_move_type_ids)
        self.assertIn(self.type_receipt, self.company.auto_je_move_type_ids)

        # Test settings onchange behavior
        settings = self.env['res.config.settings'].new({
            'company_id': self.company.id,
            'auto_svl_move_type_ids': [Command.set([self.type_receipt.id])],
            'auto_je_move_type_ids': [Command.set([self.type_receipt.id])],
        })
        # Selecting an additional JE adds it to SVL
        settings.auto_je_move_type_ids = [Command.set([self.type_receipt.id, self.type_delivery.id])]
        settings._onchange_auto_je_move_type_ids()
        self.assertIn(self.type_delivery, settings.auto_svl_move_type_ids)

        # Deselecting a type from SVL removes it from JE
        settings.auto_svl_move_type_ids = [Command.set([self.type_receipt.id])]
        settings._onchange_auto_svl_move_type_ids()
        self.assertNotIn(self.type_delivery, settings.auto_je_move_type_ids)

    def test_receipt_valuation_flow(self):
        """Receipt move creates 1 positive SVL and 1 posted Journal Entry with correct debit/credit lines."""
        self.company.write({
            'auto_svl_move_type_ids': [Command.set([self.type_receipt.id])],
            'auto_je_move_type_ids': [Command.set([self.type_receipt.id])],
        })

        qty = 3.0
        unit_cost = self.product.standard_price  # 40.0
        expected_total_value = qty * unit_cost  # 120.0

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
            'company_id': self.company.id,
        })
        move = self._create_and_confirm_move(
            self.product, self.loc_supplier, self.loc_stock, qty, picking=picking
        )
        move.quantity = qty
        move.picked = True
        move._action_done()

        # Check SVL
        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertEqual(len(svls), 1, "Receipt must create exactly 1 SVL record.")
        svl = svls[0]
        self.assertEqual(svl.quantity, qty, "Receipt SVL quantity must be positive.")
        self.assertEqual(svl.unit_cost, unit_cost)
        self.assertEqual(svl.value, expected_total_value)

        # Check Journal Entry
        account_move = svl.account_move_id
        self.assertTrue(account_move, "SVL must link to a journal entry.")
        self.assertEqual(account_move.state, 'posted', "Journal entry must be posted.")
        self.assertEqual(move.account_move_id, account_move)

        lines = account_move.line_ids
        self.assertEqual(len(lines), 2, "Journal entry must have 2 lines.")

        debit_line = lines.filtered(lambda l: l.debit > 0)
        credit_line = lines.filtered(lambda l: l.credit > 0)

        # Receipt: Debit destination valuation account, Credit source counterpart account
        self.assertEqual(debit_line.account_id, self.account_stock)
        self.assertEqual(debit_line.debit, expected_total_value)
        self.assertEqual(credit_line.account_id, self.account_interim)
        self.assertEqual(credit_line.credit, expected_total_value)

        # Check picking smart buttons
        self.assertEqual(picking.dn_account_move_count, 1)
        self.assertEqual(picking.dn_svl_count, 1)

    def test_delivery_valuation_flow(self):
        """Delivery move creates 1 negative SVL and 1 posted Journal Entry with correct debit/credit lines."""
        self.company.write({
            'auto_svl_move_type_ids': [Command.set([self.type_delivery.id])],
            'auto_je_move_type_ids': [Command.set([self.type_delivery.id])],
        })

        qty = 2.0
        unit_cost = self.product.standard_price  # 40.0
        expected_total_value = qty * unit_cost  # 80.0

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.loc_stock.id,
            'location_dest_id': self.loc_customer.id,
            'company_id': self.company.id,
        })
        move = self._create_and_confirm_move(
            self.product, self.loc_stock, self.loc_customer, qty, picking=picking
        )
        move.quantity = qty
        move.picked = True
        move._action_done()

        # Check SVL
        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertEqual(len(svls), 1, "Delivery must create exactly 1 SVL record.")
        svl = svls[0]
        self.assertEqual(svl.quantity, -qty, "Delivery SVL quantity must be negative.")
        self.assertEqual(svl.unit_cost, unit_cost)
        self.assertEqual(svl.value, -expected_total_value)

        # Check Journal Entry
        account_move = svl.account_move_id
        self.assertTrue(account_move, "SVL must link to a journal entry.")
        self.assertEqual(account_move.state, 'posted', "Journal entry must be posted.")
        self.assertEqual(move.account_move_id, account_move)

        lines = account_move.line_ids
        self.assertEqual(len(lines), 2, "Journal entry must have 2 lines.")

        debit_line = lines.filtered(lambda l: l.debit > 0)
        credit_line = lines.filtered(lambda l: l.credit > 0)

        # Delivery: Debit destination counterpart account, Credit source valuation account
        self.assertEqual(debit_line.account_id, self.account_interim)
        self.assertEqual(debit_line.debit, expected_total_value)
        self.assertEqual(credit_line.account_id, self.account_stock)
        self.assertEqual(credit_line.credit, expected_total_value)

        # Check picking smart buttons
        self.assertEqual(picking.dn_account_move_count, 1)
        self.assertEqual(picking.dn_svl_count, 1)

    def test_svl_only_without_je(self):
        """Move type enabled for SVL but disabled for JE creates SVL but no Journal Entry."""
        self.company.write({
            'auto_svl_move_type_ids': [Command.set([self.type_receipt.id])],
            'auto_je_move_type_ids': [Command.clear()],
        })

        qty = 5.0
        move = self._create_and_confirm_move(
            self.product, self.loc_supplier, self.loc_stock, qty
        )
        move.quantity = qty
        move.picked = True
        move._action_done()

        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertEqual(len(svls), 1, "SVL must be created when enabled.")
        self.assertFalse(move.account_move_id, "No Journal Entry should be created when JE is disabled.")
        self.assertFalse(svls.account_move_id, "SVL must not link to any Journal Entry.")

    def test_internal_transfer_regression(self):
        """Verify internal transfer flow continues to function properly under move type configuration."""
        self.company.write({
            'auto_svl_move_type_ids': [Command.set([self.type_internal.id])],
            'auto_je_move_type_ids': [Command.set([self.type_internal.id])],
        })

        qty = 4.0
        unit_cost = self.product.standard_price  # 40.0
        expected_total_value = qty * unit_cost  # 160.0

        move = self._create_and_confirm_move(
            self.product, self.loc_stock, self.loc_wh2, qty
        )
        move.quantity = qty
        move.picked = True
        move._action_done()

        svls = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
        self.assertEqual(len(svls), 2, "Internal transfer must create 2 SVLs.")

        svl_out = svls.filtered(lambda s: s.quantity < 0)
        svl_in = svls.filtered(lambda s: s.quantity > 0)
        self.assertEqual(svl_out.quantity, -qty)
        self.assertEqual(svl_out.value, -expected_total_value)
        self.assertEqual(svl_in.quantity, qty)
        self.assertEqual(svl_in.value, expected_total_value)

        account_move_out = svl_out.account_move_id
        account_move_in = svl_in.account_move_id
        self.assertTrue(account_move_out)
        self.assertTrue(account_move_in)
        self.assertNotEqual(account_move_out, account_move_in)
        self.assertEqual(account_move_out.state, 'posted')
        self.assertEqual(account_move_in.state, 'posted')

        transit_account = move._get_interim_transit_account()

        lines_out = account_move_out.line_ids
        debit_line_out = lines_out.filtered(lambda l: l.debit > 0)
        credit_line_out = lines_out.filtered(lambda l: l.credit > 0)
        self.assertEqual(credit_line_out.account_id, self.account_stock)
        self.assertEqual(credit_line_out.credit, expected_total_value)
        self.assertEqual(debit_line_out.account_id, transit_account)
        self.assertEqual(debit_line_out.debit, expected_total_value)

        lines_in = account_move_in.line_ids
        debit_line_in = lines_in.filtered(lambda l: l.debit > 0)
        credit_line_in = lines_in.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line_in.account_id, self.account_wh2)
        self.assertEqual(debit_line_in.debit, expected_total_value)
        self.assertEqual(credit_line_in.account_id, transit_account)
        self.assertEqual(credit_line_in.credit, expected_total_value)

        # Transit account balances to zero across both journal entries
        transit_lines = (lines_out | lines_in).filtered(lambda l: l.account_id == transit_account)
        self.assertEqual(
            sum(transit_lines.mapped('debit')),
            sum(transit_lines.mapped('credit')),
            "Transit account must balance to zero across both journal entries."
        )
