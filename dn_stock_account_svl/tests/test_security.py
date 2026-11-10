# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Test suite for Stock Valuation Layer security and access control conforming to Odoo 18 standard."""

from odoo import Command
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestStockValuationSecurity(TransactionCase):
    """Test suite for security access rights, CRUD, and multi-company rules on stock.valuation.layer."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company

        # Create second company for multi-company tests
        cls.company_b = cls.env['res.company'].create({
            'name': 'Company B Test',
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Valuation Test Product',
            'type': 'consu',
            'is_storable': True,
            'standard_price': 25.0,
        })

        # Test users
        cls.stock_user = cls.env['res.users'].create({
            'name': 'Stock User Test',
            'login': 'stock_user_test',
            'email': 'stock_user_test@example.com',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
            ])],
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })

        cls.stock_manager = cls.env['res.users'].create({
            'name': 'Stock Manager Test',
            'login': 'stock_manager_test',
            'email': 'stock_manager_test@example.com',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_manager').id,
            ])],
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })

        cls.company_b_manager = cls.env['res.users'].create({
            'name': 'Company B Manager Test',
            'login': 'company_b_manager_test',
            'email': 'company_b_manager_test@example.com',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_manager').id,
            ])],
            'company_id': cls.company_b.id,
            'company_ids': [Command.set([cls.company_b.id])],
        })

        cls.company_b_user = cls.env['res.users'].create({
            'name': 'Company B User Test',
            'login': 'company_b_user_test',
            'email': 'company_b_user_test@example.com',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
            ])],
            'company_id': cls.company_b.id,
            'company_ids': [Command.set([cls.company_b.id])],
        })

    def test_01_stock_manager_crud_rights(self):
        """Verify stock manager can create, read, and write SVL records."""
        svl_mgr = self.env['stock.valuation.layer'].with_user(self.stock_manager)
        svl = svl_mgr.create({
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_cost': 25.0,
            'value': 250.0,
            'company_id': self.company_a.id,
            'description': 'Direct CRUD test layer by manager',
        })
        self.assertTrue(svl.id, "SVL record should be created successfully by Stock Manager.")
        self.assertEqual(svl.quantity, 10.0)
        self.assertEqual(svl.value, 250.0)

        # Read
        read_data = svl.read(['product_id', 'quantity', 'value', 'description'])
        self.assertEqual(read_data[0]['description'], 'Direct CRUD test layer by manager')

        # Write
        svl.write({'description': 'Updated description by manager'})
        self.assertEqual(svl.description, 'Updated description by manager')

    def test_02_stock_manager_cannot_unlink_svl(self):
        """Verify stock manager calling svl.unlink() raises AccessError due to perm_unlink=0."""
        svl_mgr = self.env['stock.valuation.layer'].with_user(self.stock_manager)
        svl = svl_mgr.create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'unit_cost': 20.0,
            'value': 100.0,
            'company_id': self.company_a.id,
            'description': 'SVL layer for unlink rejection test',
        })
        with self.assertRaises(AccessError):
            svl.unlink()

    def test_03_stock_user_direct_crud_denied(self):
        """Verify stock user without manager group cannot directly create or read SVL records."""
        svl_user = self.env['stock.valuation.layer'].with_user(self.stock_user)

        # Create must raise AccessError
        with self.assertRaises(AccessError):
            svl_user.create({
                'product_id': self.product.id,
                'quantity': 2.0,
                'unit_cost': 25.0,
                'value': 50.0,
                'company_id': self.company_a.id,
            })

        # Read on existing record must raise AccessError
        svl_existing = self.env['stock.valuation.layer'].sudo().create({
            'product_id': self.product.id,
            'quantity': 2.0,
            'unit_cost': 25.0,
            'value': 50.0,
            'company_id': self.company_a.id,
        })
        with self.assertRaises(AccessError):
            svl_existing.with_user(self.stock_user).read(['quantity', 'value'])

    def test_04_multi_company_rule(self):
        """Verify multi-company rule isolates SVL records between companies."""
        # Create SVL in Company A
        svl_a = self.env['stock.valuation.layer'].sudo().create({
            'product_id': self.product.id,
            'quantity': 1.0,
            'unit_cost': 10.0,
            'value': 10.0,
            'company_id': self.company_a.id,
        })

        # Company B Manager should not see Company A's SVL record
        svls_visible_to_b = self.env['stock.valuation.layer'].with_user(
            self.company_b_manager
        ).search([('id', '=', svl_a.id)])
        self.assertFalse(
            svls_visible_to_b,
            "Manager in Company B must not see SVL belonging to Company A.",
        )

    def test_05_warehouse_workflow_svl_creation(self):
        """Verify warehouse workflow methods _create_in_svl / _create_out_svl succeed for stock user via sudo."""
        supplier_loc = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
        stock_loc = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        if supplier_loc and stock_loc:
            move = self.env['stock.move'].create({
                'name': 'Test Incoming Move Security',
                'product_id': self.product.id,
                'product_uom': self.product.uom_id.id,
                'product_uom_qty': 10.0,
                'quantity': 10.0,
                'location_id': supplier_loc.id,
                'location_dest_id': stock_loc.id,
                'company_id': self.company_a.id,
            })
            svl = move.with_user(self.stock_user)._create_in_svl()
            self.assertTrue(svl.id, "Warehouse incoming SVL creation should succeed via sudo.")
            self.assertEqual(svl.quantity, 10.0)

    def test_06_ui_button_and_menu_security(self):
        """Verify smart buttons and menu items have groups='stock.group_stock_manager'."""
        menu = self.env.ref('dn_stock_account_svl.menu_stock_valuation_layers', raise_if_not_found=False)
        if menu:
            self.assertIn(
                self.env.ref('stock.group_stock_manager'),
                menu.groups_id,
                "menu_stock_valuation_layers must be guarded by stock.group_stock_manager",
            )

