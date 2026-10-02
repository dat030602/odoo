# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
            ])],
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
        })

        cls.stock_manager = cls.env['res.users'].create({
            'name': 'Stock Manager Test',
            'login': 'stock_manager_test',
            'email': 'stock_manager_test@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_manager').id,
            ])],
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
        })

        cls.company_b_user = cls.env['res.users'].create({
            'name': 'Company B User Test',
            'login': 'company_b_user_test',
            'email': 'company_b_user_test@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
            ])],
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
        })

    def test_01_stock_valuation_layer_crud(self):
        """Test basic CRUD operations on stock.valuation.layer."""
        # Create
        svl = self.env['stock.valuation.layer'].create({
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_cost': 25.0,
            'value': 250.0,
            'company_id': self.company_a.id,
            'description': 'Direct CRUD test layer',
        })
        self.assertTrue(svl.id, "SVL record should be created successfully.")
        self.assertEqual(svl.quantity, 10.0)
        self.assertEqual(svl.value, 250.0)

        # Read
        read_data = svl.read(['product_id', 'quantity', 'value', 'description'])
        self.assertEqual(read_data[0]['description'], 'Direct CRUD test layer')

        # Write
        svl.write({'description': 'Updated description'})
        self.assertEqual(svl.description, 'Updated description')

        # Unlink
        svl_id = svl.id
        svl.unlink()
        self.assertFalse(self.env['stock.valuation.layer'].browse(svl_id).exists())

    def test_02_stock_user_access_rights(self):
        """Verify stock user can create and read SVL records."""
        svl_env_user = self.env['stock.valuation.layer'].with_user(self.stock_user)
        svl = svl_env_user.create({
            'product_id': self.product.id,
            'quantity': 2.0,
            'unit_cost': 25.0,
            'value': 50.0,
            'company_id': self.company_a.id,
        })
        self.assertTrue(svl.id)
        # Reading should succeed
        self.assertEqual(svl.with_user(self.stock_user).quantity, 2.0)

    def test_03_stock_manager_access_rights(self):
        """Verify stock manager can create, read, write, and delete SVL records."""
        svl_env_mgr = self.env['stock.valuation.layer'].with_user(self.stock_manager)
        svl = svl_env_mgr.create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'unit_cost': 20.0,
            'value': 100.0,
            'company_id': self.company_a.id,
        })
        self.assertTrue(svl.id)
        svl.write({'unit_cost': 30.0, 'value': 150.0})
        self.assertEqual(svl.value, 150.0)
        svl.unlink()
        self.assertFalse(svl.exists())

    def test_04_multi_company_isolation(self):
        """Verify multi-company rule isolates SVL records between companies."""
        # Create SVL in Company A
        svl_a = self.env['stock.valuation.layer'].create({
            'product_id': self.product.id,
            'quantity': 1.0,
            'unit_cost': 10.0,
            'value': 10.0,
            'company_id': self.company_a.id,
        })

        # Company B user should not see Company A's SVL record
        svls_visible_to_b = self.env['stock.valuation.layer'].with_user(
            self.company_b_user
        ).search([('id', '=', svl_a.id)])
        self.assertFalse(
            svls_visible_to_b,
            "User in Company B must not see SVL belonging to Company A."
        )
