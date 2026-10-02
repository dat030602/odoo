# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestStockLocationValuation(TransactionCase):
    """Test suite for stock.location valuation account resolution and CRUD."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Create valuation accounts for testing
        cls.account_type = cls.env.ref('account.data_account_type_current_assets', raise_if_not_found=False)
        account_type_id = 'asset_current'

        cls.account_parent = cls.env['account.account'].create({
            'name': 'Parent Location Valuation Account',
            'code': '1010101',
            'account_type': account_type_id,
            'company_ids': [cls.company.id],
        })
        cls.account_child = cls.env['account.account'].create({
            'name': 'Child Location Valuation Account',
            'code': '1010102',
            'account_type': account_type_id,
            'company_ids': [cls.company.id],
        })
        cls.account_categ = cls.env['account.account'].create({
            'name': 'Category Fallback Valuation Account',
            'code': '1010103',
            'account_type': account_type_id,
            'company_ids': [cls.company.id],
        })

        # Create product category with valuation account
        cls.product_category = cls.env['product.category'].create({
            'name': 'Test Category With Valuation',
            'property_stock_valuation_account_id': cls.account_categ.id,
        })
        cls.product_category_no_acc = cls.env['product.category'].create({
            'name': 'Test Category Without Valuation',
        })

        # Create product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Storable Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.product_category.id,
            'standard_price': 100.0,
        })

        # Create locations hierarchy
        cls.parent_location = cls.env['stock.location'].create({
            'name': 'Parent Warehouse Location',
            'usage': 'internal',
            'dn_valuation_account_id': cls.account_parent.id,
        })
        cls.child_location = cls.env['stock.location'].create({
            'name': 'Child Shelf Location',
            'usage': 'internal',
            'location_id': cls.parent_location.id,
        })
        cls.grandchild_location = cls.env['stock.location'].create({
            'name': 'Grandchild Bin Location',
            'usage': 'internal',
            'location_id': cls.child_location.id,
        })
        cls.standalone_location = cls.env['stock.location'].create({
            'name': 'Standalone Location Without Account',
            'usage': 'internal',
        })

    def test_01_direct_valuation_account(self):
        """Verify that direct dn_valuation_account_id on location is resolved first."""
        self.assertEqual(
            self.parent_location._get_valuation_account(self.product),
            self.account_parent,
            "Direct valuation account on the location should take top precedence."
        )

    def test_02_parent_location_inheritance(self):
        """Verify that child location inherits valuation account from parent."""
        self.assertFalse(self.child_location.dn_valuation_account_id)
        resolved_account = self.child_location._get_valuation_account(self.product)
        self.assertEqual(
            resolved_account,
            self.account_parent,
            "Child location without account should inherit from its parent location."
        )

    def test_03_grandchild_recursive_inheritance(self):
        """Verify recursive ancestor traversal for nested locations."""
        self.assertFalse(self.grandchild_location.dn_valuation_account_id)
        resolved_account = self.grandchild_location._get_valuation_account(self.product)
        self.assertEqual(
            resolved_account,
            self.account_parent,
            "Grandchild location should resolve account from grandparent location."
        )

    def test_04_child_override_parent_account(self):
        """Verify that assigning an account to child overrides parent's account."""
        self.child_location.dn_valuation_account_id = self.account_child.id
        self.assertEqual(
            self.child_location._get_valuation_account(self.product),
            self.account_child,
            "Child location direct account must override parent's account."
        )
        # Grandchild should now inherit from child_location
        self.assertEqual(
            self.grandchild_location._get_valuation_account(self.product),
            self.account_child,
            "Grandchild should inherit from nearest ancestor."
        )

    def test_05_fallback_to_product_category(self):
        """Verify fallback to product category when location tree has no account."""
        self.assertFalse(self.standalone_location.dn_valuation_account_id)
        resolved_account = self.standalone_location._get_valuation_account(self.product)
        self.assertEqual(
            resolved_account,
            self.account_categ,
            "Should fall back to product category property_stock_valuation_account_id."
        )

    def test_06_fallback_company_default_when_category_has_no_account(self):
        """Verify fallback resolves company-dependent default when category has no direct account."""
        product_no_acc = self.env['product.product'].create({
            'name': 'Product Without Direct Valuation Account',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.product_category_no_acc.id,
        })
        resolved_account = self.standalone_location._get_valuation_account(product_no_acc)
        self.assertTrue(
            resolved_account,
            "Should resolve company-dependent fallback stock valuation account."
        )

    def test_07_get_valuation_account_without_product(self):
        """Verify _get_valuation_account handles product=None safely."""
        account = self.parent_location._get_valuation_account(product=None)
        self.assertEqual(account, self.account_parent)

        empty_account = self.standalone_location._get_valuation_account(product=None)
        self.assertFalse(empty_account)

    def test_08_location_crud_operations(self):
        """Verify CRUD operations on stock.location with dn_valuation_account_id."""
        loc = self.env['stock.location'].create({
            'name': 'CRUD Test Location',
            'usage': 'internal',
            'dn_valuation_account_id': self.account_child.id,
        })
        self.assertEqual(loc.dn_valuation_account_id, self.account_child)

        # Update
        loc.write({'dn_valuation_account_id': self.account_parent.id})
        self.assertEqual(loc.dn_valuation_account_id, self.account_parent)

        # Clear
        loc.write({'dn_valuation_account_id': False})
        self.assertFalse(loc.dn_valuation_account_id)

        # Unlink
        loc_id = loc.id
        loc.unlink()
        self.assertFalse(self.env['stock.location'].browse(loc_id).exists())
