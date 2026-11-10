# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
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
            'name': 'Category Valuation Account',
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

        # Products with different configurations
        cls.product_default = cls.env['product.product'].create({
            'name': 'Test Storable Product (Default)',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.product_category.id,
            'standard_price': 100.0,
            'use_location_valuation_account': False,
        })
        cls.product = cls.product_default

        cls.product_use_location = cls.env['product.product'].create({
            'name': 'Test Storable Product (Use Location)',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.product_category.id,
            'standard_price': 100.0,
            'use_location_valuation_account': True,
        })

        cls.product_no_acc = cls.env['product.product'].create({
            'name': 'Product Without Direct Category Account',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.product_category_no_acc.id,
            'use_location_valuation_account': False,
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

    def test_01_default_product_prioritizes_category_account(self):
        """When use_location_valuation_account is False (default) and both have accounts, Category account is returned."""
        resolved = self.parent_location._get_valuation_account(self.product_default)
        self.assertEqual(
            resolved,
            self.account_categ,
            "Default behavior must prioritize product category valuation account over location account."
        )

    def test_02_default_product_falls_back_to_location_account(self):
        """When use_location_valuation_account is False and category has no account, location account is used as fallback."""
        self.company.account_stock_valuation_id = False
        resolved = self.parent_location._get_valuation_account(self.product_no_acc)
        self.assertEqual(
            resolved,
            self.account_parent,
            "When category has no valuation account, location account must be used as fallback."
        )

    def test_03_use_location_flag_prioritizes_location_account(self):
        """When use_location_valuation_account is True and both have accounts, Location account is returned."""
        resolved = self.parent_location._get_valuation_account(self.product_use_location)
        self.assertEqual(
            resolved,
            self.account_parent,
            "Flagged product must prioritize location valuation account over category account."
        )

    def test_04_use_location_flag_falls_back_to_category_account(self):
        """When use_location_valuation_account is True and location has no account, category account is used as fallback."""
        resolved = self.standalone_location._get_valuation_account(self.product_use_location)
        self.assertEqual(
            resolved,
            self.account_categ,
            "When location has no valuation account, category account must be used as fallback."
        )

    def test_05_location_hierarchy_inheritance_with_use_location(self):
        """Verify child and grandchild locations inherit valuation account when using location priority."""
        self.assertEqual(
            self.child_location._get_valuation_account(self.product_use_location),
            self.account_parent,
            "Child location should inherit valuation account from parent location."
        )
        self.assertEqual(
            self.grandchild_location._get_valuation_account(self.product_use_location),
            self.account_parent,
            "Grandchild location should resolve account from grandparent location."
        )

    def test_06_child_override_parent_account_with_use_location(self):
        """Verify child location override takes precedence over parent location."""
        self.child_location.dn_valuation_account_id = self.account_child.id
        self.assertEqual(
            self.child_location._get_valuation_account(self.product_use_location),
            self.account_child,
            "Child location direct account must override parent's account."
        )
        self.assertEqual(
            self.grandchild_location._get_valuation_account(self.product_use_location),
            self.account_child,
            "Grandchild should inherit from nearest ancestor."
        )

    def test_07_user_error_when_neither_category_nor_location_has_account(self):
        """Verify UserError is raised when neither category nor location has an account."""
        self.company.account_stock_valuation_id = False
        with self.assertRaises(UserError):
            self.standalone_location._get_valuation_account(self.product_no_acc)

    def test_08_get_valuation_account_without_product(self):
        """Verify _get_valuation_account handles product=None."""
        account = self.parent_location._get_valuation_account(product=None)
        self.assertEqual(account, self.account_parent)

        with self.assertRaises(UserError):
            self.standalone_location._get_valuation_account(product=None)

    def test_09_location_crud_operations(self):
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
