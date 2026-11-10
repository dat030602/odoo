# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCostingMethods(TransactionCase):
    """Test suite for Standard, AVCO, and FIFO costing methods on Stock Valuation Layer."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        # Accounts
        cls.account_stock = cls.env['account.account'].create({
            'name': 'Stock Valuation Account Costing',
            'code': '1010311',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        cls.account_interim = cls.env['account.account'].create({
            'name': 'Stock Interim Account Costing',
            'code': '1010312',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })

        # Journal
        cls.stock_journal = cls.company.account_stock_journal_id
        if not cls.stock_journal:
            cls.stock_journal = cls.env['account.journal'].create({
                'name': 'Stock Journal Costing Test',
                'type': 'general',
                'code': 'STKCS',
                'company_id': cls.company.id,
            })
            cls.company.account_stock_journal_id = cls.stock_journal.id

        # Categories
        cls.category_standard = cls.env['product.category'].create({
            'name': 'Standard Costing Category',
            'property_cost_method': 'standard',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.account_stock.id,
        })
        cls.category_avco = cls.env['product.category'].create({
            'name': 'AVCO Costing Category',
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.account_stock.id,
        })
        cls.category_fifo = cls.env['product.category'].create({
            'name': 'FIFO Costing Category',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.account_stock.id,
        })

        # Products
        cls.product_standard = cls.env['product.product'].create({
            'name': 'Product Standard Costing',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category_standard.id,
            'standard_price': 100.0,
        })
        cls.product_avco = cls.env['product.product'].create({
            'name': 'Product AVCO Costing',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category_avco.id,
            'standard_price': 100.0,
        })
        cls.product_fifo = cls.env['product.product'].create({
            'name': 'Product FIFO Costing',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category_fifo.id,
            'standard_price': 100.0,
        })

        # Locations
        cls.loc_stock = cls.env['stock.location'].create({
            'name': 'Stock Costing Test',
            'usage': 'internal',
            'dn_valuation_account_id': cls.account_stock.id,
        })
        cls.loc_supplier = cls.env['stock.location'].create({
            'name': 'Supplier Costing Test',
            'usage': 'supplier',
            'dn_valuation_account_id': cls.account_interim.id,
        })
        cls.loc_customer = cls.env['stock.location'].create({
            'name': 'Customer Costing Test',
            'usage': 'customer',
            'dn_valuation_account_id': cls.account_interim.id,
        })

    def test_01_standard_costing_in_and_out(self):
        """Test Standard costing calculates SVL based on product standard_price."""
        product = self.product_standard
        move_in = self.env['stock.move'].create({
            'name': 'Receipt Standard',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
        })
        svls_in = move_in._create_in_svl(forced_quantity=10.0)
        self.assertEqual(len(svls_in), 1)
        self.assertEqual(svls_in.unit_cost, 100.0)
        self.assertEqual(svls_in.value, 1000.0)
        self.assertEqual(svls_in.remaining_qty, 0.0)

        move_out = self.env['stock.move'].create({
            'name': 'Delivery Standard',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 4.0,
            'location_id': self.loc_stock.id,
            'location_dest_id': self.loc_customer.id,
        })
        svls_out = move_out._create_out_svl(forced_quantity=4.0)
        self.assertEqual(len(svls_out), 1)
        self.assertEqual(svls_out.unit_cost, 100.0)
        self.assertEqual(svls_out.value, -400.0)

    def test_02_avco_costing_weighted_average(self):
        """Test AVCO recomputes standard_price on inbound moves."""
        product = self.product_avco
        product.standard_price = 100.0

        # Initial layer: 10 units @ 100.0 = 1000.0
        self.env['stock.valuation.layer'].create({
            'product_id': product.id,
            'quantity': 10.0,
            'unit_cost': 100.0,
            'value': 1000.0,
            'company_id': self.company.id,
            'description': 'Initial AVCO layer',
        })

        # New inbound: 10 units @ 150.0 = 1500.0
        move_in = self.env['stock.move'].create({
            'name': 'Receipt AVCO 2',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
        })
        # Mock price_unit to 150.0
        move_in._recompute_product_avco(10.0, 1500.0)
        # New standard price: (1000 + 1500) / (10 + 10) = 2500 / 20 = 125.0
        self.assertEqual(product.standard_price, 125.0)

    def test_03_fifo_costing_layer_consumption(self):
        """Test FIFO consumes candidate layers in chronological order."""
        product = self.product_fifo

        # Layer 1: 5 units @ 10.0 = 50.0
        layer1 = self.env['stock.valuation.layer'].create({
            'product_id': product.id,
            'quantity': 5.0,
            'unit_cost': 10.0,
            'value': 50.0,
            'remaining_qty': 5.0,
            'remaining_value': 50.0,
            'company_id': self.company.id,
            'description': 'FIFO Batch 1',
        })
        # Layer 2: 5 units @ 20.0 = 100.0
        layer2 = self.env['stock.valuation.layer'].create({
            'product_id': product.id,
            'quantity': 5.0,
            'unit_cost': 20.0,
            'value': 100.0,
            'remaining_qty': 5.0,
            'remaining_value': 100.0,
            'company_id': self.company.id,
            'description': 'FIFO Batch 2',
        })

        move_out = self.env['stock.move'].create({
            'name': 'Delivery FIFO',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 7.0,
            'location_id': self.loc_stock.id,
            'location_dest_id': self.loc_customer.id,
        })

        # Consume 7 units: 5 from layer1 (5*10=50) + 2 from layer2 (2*20=40) = 90 total value
        svls_out = move_out._create_out_svl(forced_quantity=7.0)
        self.assertEqual(svls_out.value, -90.0)
        self.assertEqual(layer1.remaining_qty, 0.0)
        self.assertEqual(layer2.remaining_qty, 3.0)
        self.assertEqual(layer2.remaining_value, 60.0)

    def test_04_fifo_restore_candidates_on_decrease(self):
        """Test restoring candidate layers on outbound decrease."""
        product = self.product_fifo
        # Layer with consumed quantity: 10 original, 3 remaining
        layer = self.env['stock.valuation.layer'].create({
            'product_id': product.id,
            'quantity': 10.0,
            'unit_cost': 20.0,
            'value': 200.0,
            'remaining_qty': 3.0,
            'remaining_value': 60.0,
            'company_id': self.company.id,
            'description': 'Partially consumed FIFO layer',
        })

        move = self.env['stock.move'].create({
            'name': 'Delivery Decrease FIFO',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'location_id': self.loc_stock.id,
            'location_dest_id': self.loc_customer.id,
        })

        # Restore 4 units back
        restored_val, unit_cost = move._restore_fifo_candidates_on_decrease(4.0, self.company)
        self.assertEqual(restored_val, 80.0)
        self.assertEqual(unit_cost, 20.0)
        self.assertEqual(layer.remaining_qty, 7.0)
        self.assertEqual(layer.remaining_value, 140.0)
