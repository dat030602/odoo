# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo import Command


@tagged('post_install', '-at_install')
class TestPackingList(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Multi-company setup
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})

        # Users & Security Groups
        cls.group_pl_user = cls.env.ref('dn_packing_list.group_packing_list_user')
        cls.group_pl_manager = cls.env.ref('dn_packing_list.group_packing_list_manager')

        cls.user_pl_user = cls.env['res.users'].create({
            'name': 'PL User',
            'login': 'pl_user_test',
            'email': 'pl_user@example.com',
            'company_id': cls.company.id,
            'company_ids': [Command.link(cls.company.id)],
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.group_pl_user.id
            ])]
        })

        cls.user_pl_manager = cls.env['res.users'].create({
            'name': 'PL Manager',
            'login': 'pl_manager_test',
            'email': 'pl_manager@example.com',
            'company_id': cls.company.id,
            'company_ids': [Command.link(cls.company.id)],
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.group_pl_manager.id
            ])]
        })

        cls.user_company_b = cls.env['res.users'].create({
            'name': 'User Comp B',
            'login': 'user_comp_b_test',
            'email': 'comp_b_user@example.com',
            'company_id': cls.company_b.id,
            'company_ids': [Command.link(cls.company_b.id)],
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.group_pl_manager.id
            ])]
        })

        # Customer partner
        cls.customer = cls.env['res.partner'].create({
            'name': 'ZZTEST Customer Logistics Ltd',
            'email': 'customer@test-logistics.com',
            'company_id': cls.company.id,
        })

        # Delivery address
        cls.delivery_address = cls.env['res.partner'].create({
            'name': 'ZZTEST Warehouse Destination',
            'parent_id': cls.customer.id,
            'type': 'delivery',
        })

        # UoMs
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_cm = cls.env.ref('uom.product_uom_cm')
        cls.uom_meter = cls.env.ref('uom.product_uom_meter')
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.uom_lb = cls.env.ref('uom.product_uom_lb')

        # Test Product
        cls.product = cls.env['product.product'].create({
            'name': 'ZZTEST Heavy Duty Boxed Unit',
            'type': 'consu',
            'is_storable': True,
            'uom_id': cls.uom_unit.id,
            'weight': 2.5,
        })

        # Carton Type
        cls.carton_type = cls.env['carton.type'].create({
            'name': 'Standard Box A',
            'code': 'BOX-A',
            'type': 'carton',
            'length': 50.0,   # 50 cm
            'width': 40.0,    # 40 cm
            'height': 30.0,   # 30 cm
            'weight': 1.2,    # 1.2 kg
            'qty_per_carton': 10.0,
            'partner_id': cls.customer.id,
        })

        # Pallet Type
        cls.pallet_type = cls.env['carton.type'].create({
            'name': 'Standard Pallet A',
            'code': 'PAL-A',
            'type': 'pallet',
            'length': 120.0,
            'width': 100.0,
            'height': 15.0,
            'weight': 15.0,
            'partner_id': cls.customer.id,
        })

        # Sales Order
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'partner_shipping_id': cls.delivery_address.id,
            'order_line': [
                Command.create({
                    'product_id': cls.product.id,
                    'product_uom_qty': 20.0,
                    'price_unit': 150.0,
                })
            ]
        })
        cls.sale_order.action_confirm()
        cls.sale_order_line = cls.sale_order.order_line[0]

        # Initial Stage
        cls.stage_new = cls.env.ref('dn_packing_list.dn_packing_list_stage__new', raise_if_not_found=False)
        if not cls.stage_new:
            cls.stage_new = cls.env['packing.list.stage'].search([('name', '=', 'New')], limit=1)

    def test_ac1_packing_list_creation_and_sequence(self):
        """Test packing list creation, code assignment, and default stage."""
        pl = self.env['packing.list'].create({
            'title': 'Test Shipment North',
            'customer': self.customer.id,
            'delivery_address': self.delivery_address.id,
            'orders': [Command.link(self.sale_order.id)],
        })
        self.assertTrue(pl.code, "Packing list code should be automatically generated from sequence.")
        self.assertIn(pl.code, pl.name, "Name should incorporate code.")
        self.assertIn("Test Shipment North", pl.name, "Name should incorporate title.")
        self.assertTrue(pl.stage_id, "Packing list should be assigned a default stage.")
        if self.stage_new:
            self.assertEqual(pl.stage_id.id, self.stage_new.id, "Initial stage should be New.")

    def test_ac2_line_computations_and_uom_conversion(self):
        """Test dimensions, CBM, weight calculations and target UoM conversions."""
        pl = self.env['packing.list'].create({
            'title': 'Test Line Computations',
            'customer': self.customer.id,
            'delivery_address': self.delivery_address.id,
        })

        line = self.env['packing.list.line'].create({
            'packing_list_id': pl.id,
            'product_id': self.product.id,
            'quantity': 20.0,
            'unit_price': 150.0,
            'ctn_type_id': self.carton_type.id,
            'type_pallet_id': self.pallet_type.id,
            'product_net_weight': 2.5,
            'distance_uom_id': self.uom_cm.id,
            'target_distance_uom_id': self.uom_meter.id,
            'weight_uom_id': self.uom_kg.id,
            'target_weight_uom_id': self.uom_lb.id,
        })
        
        # Test onchange for carton
        line._onchange_ctn_type_id()
        self.assertEqual(line.length, 50.0)
        self.assertEqual(line.qty_per_carton, 10.0)
        
        # Test carton quantity compute
        line._onchange_carton_qty()
        self.assertEqual(line.carton_quantity, 2.0, "Carton qty should be quantity / qty_per_carton")

        # Test onchange for pallet
        line._onchange_type_pallet_id()
        self.assertEqual(line.pallet_length, 120.0)
        self.assertEqual(line.pallet_net_weight, 15.0)

        # CBM: 50 * 40 * 30 / 1,000,000 = 0.06 m³ per carton
        self.assertAlmostEqual(line.ctn_cbm, 0.06, places=4, msg="Carton CBM should be 0.06 m³.")
        self.assertAlmostEqual(line.ctn_total_cbm, 0.12, places=4, msg="Total Carton CBM for 2 cartons should be 0.12 m³.")

        # Weights: 20 * 2.5 kg = 50 kg Net Weight
        self.assertAlmostEqual(line.net_weight, 50.0, places=2)
        # Gross weight: 50 kg + 2 * 1.2 kg = 52.4 kg
        self.assertAlmostEqual(line.gross_weight, 52.4, places=2)

        # Target distance conversion (cm -> m): 50 cm = 0.5 m
        self.assertAlmostEqual(line.target_length, 0.5, places=2)
        self.assertAlmostEqual(line.target_width, 0.4, places=2)
        self.assertAlmostEqual(line.target_height, 0.3, places=2)

        # Target weight conversion (kg -> lb): 50 kg ≈ 110.23 lb
        self.assertGreater(line.target_net_weight, 100.0)

    def test_ac3_header_totals(self):
        """Test stored totals computation."""
        pl = self.env['packing.list'].create({
            'title': 'Test Totals',
            'customer': self.customer.id,
            'delivery_address': self.delivery_address.id,
            'orders': [Command.link(self.sale_order.id)],
        })

        self.env['packing.list.line'].create({
            'packing_list_id': pl.id,
            'order_line_id': self.sale_order_line.id,
            'product_id': self.product.id,
            'quantity': 12.0,
            'unit_price': 150.0,
            'carton_quantity': 2.0,
            'product_net_weight': 2.5,
            'pallet_qty': 1.0,
        })

        self.env['packing.list.line'].create({
            'packing_list_id': pl.id,
            'order_line_id': self.sale_order_line.id,
            'product_id': self.product.id,
            'quantity': 8.0,
            'unit_price': 150.0,
            'carton_quantity': 1.0,
            'product_net_weight': 2.5,
            'pallet_qty': 1.0,
        })

        # Header totals verification
        self.assertEqual(pl.total_quantity, 20.0, "Total quantity should be 20.0")
        self.assertEqual(pl.number_cartons, 3.0, "Total cartons should be 3.0")
        self.assertEqual(pl.total_amount, 3000.0, "Total amount should be 3,000.0")
        self.assertEqual(pl.total_pallet_quantity, 2.0, "Total pallet quantity should be 2.0")

    def test_ac3_quota_validation_prevents_overpack(self):
        """Test that packable_remaining_qty constrains prevent allocating more than ordered."""
        pl = self.env['packing.list'].create({
            'title': 'Test Quota',
            'customer': self.customer.id,
            'delivery_address': self.delivery_address.id,
            'orders': [Command.link(self.sale_order.id)],
        })

        with self.assertRaises(ValidationError):
            self.env['packing.list.line'].create({
                'packing_list_id': pl.id,
                'order_line_id': self.sale_order_line.id,
                'product_id': self.product.id,
                'quantity': 25.0,
            })

    def test_ac3_invoice_line_preparation(self):
        """Test invoice line preparation without singleton error."""
        pl = self.env['packing.list'].create({
            'title': 'Test Invoice',
            'customer': self.customer.id,
            'delivery_address': self.delivery_address.id,
            'orders': [Command.link(self.sale_order.id)],
        })

        self.env['packing.list.line'].create({
            'packing_list_id': pl.id,
            'order_line_id': self.sale_order_line.id,
            'product_id': self.product.id,
            'quantity': 12.0,
            'unit_price': 150.0,
        })

        self.env['packing.list.line'].create({
            'packing_list_id': pl.id,
            'order_line_id': self.sale_order_line.id,
            'product_id': self.product.id,
            'quantity': 8.0,
            'unit_price': 150.0,
        })

        invoice_vals = self.sale_order_line.with_context(
            default_x_packing_list_id=pl.id
        )._prepare_invoice_line()
        self.assertEqual(invoice_vals.get('quantity'), 20.0, "Invoice quantity should sum all matching PL lines (12 + 8).")
        self.assertEqual(invoice_vals.get('price_unit'), 150.0, "Invoice unit price should be preserved.")

    def test_ac3_workflows(self):
        """Test move_forward, move_back, button_cancel, action_create_child_packing_list, action_deliver, action_create_invoice."""
        pl = self.env['packing.list'].create({
            'title': 'Test Workflow',
            'customer': self.customer.id,
            'delivery_address': self.delivery_address.id,
            'orders': [Command.link(self.sale_order.id)],
        })
        
        self.env['packing.list.line'].create({
            'packing_list_id': pl.id,
            'order_line_id': self.sale_order_line.id,
            'product_id': self.product.id,
            'quantity': 10.0,
            'is_checked': True,
        })
        
        initial_stage = pl.stage_id
        # Test move_forward and move_back
        pl.move_forward()
        self.assertNotEqual(pl.stage_id.id, initial_stage.id, "Should move to next stage")
        pl.move_back()
        self.assertEqual(pl.stage_id.id, initial_stage.id, "Should move back to initial stage")
        
        # Test cancel
        pl.button_cancel()
        self.assertEqual(pl.stage_id.name, 'Cancelled', "Stage should be Cancelled")
        pl.stage_id = initial_stage.id # Reset for split test
        
        # Test split into child packing list
        action = pl.action_create_child_packing_list()
        self.assertTrue(action, "Should return an action")
        child_pl = self.env['packing.list'].search([('parent_packing_list_id', '=', pl.id)])
        self.assertTrue(child_pl, "Child packing list should be created")
        
        # Test Deliver action
        pl.action_deliver()
        self.assertEqual(pl.stage_id.name, 'Delivered', "Stage should be Delivered after deliver action")
        
        # Test Invoice action
        pl.action_create_invoice()
        self.assertEqual(pl.stage_id.name, 'Invoiced', "Stage should be Invoiced after invoice action")

    def test_ac4_add_to_packing_list_wizard(self):
        """Test wizard creation and line loading."""
        wizard = self.env['add.to.packing.list.wizard'].with_context(
            active_id=self.sale_order.id,
            active_model='sale.order',
            active_ids=[self.sale_order.id]
        ).create({
            'partner_id': self.customer.id,
            'name': 'Wizard PL',
            'order_ids': [Command.link(self.sale_order.id)],
        })
        
        # load lines
        wizard.load_all_order_lines()
        self.assertTrue(wizard.order_line_wizard_ids, "Wizard lines should be loaded")
        
        # confirm form
        wizard.confirm_form()
        pl = self.env['packing.list'].search([('title', '=', 'Wizard PL')])
        self.assertTrue(pl, "Packing list should be created by wizard")
        self.assertEqual(pl.delivery_address.id, self.delivery_address.id, "Delivery address should be integer ID")

    def test_ac5_security_multi_company(self):
        """Test multi-company visibility and user access groups."""
        # User 1 (PL User) can create
        pl_user_env = self.env['packing.list'].with_user(self.user_pl_user)
        pl_user_pl = pl_user_env.create({
            'title': 'User 1 PL',
            'customer': self.customer.id,
        })
        self.assertTrue(pl_user_pl, "PL User should be able to create PL")
        
        # User 1 CANNOT unlink stages
        stage = self.env['packing.list.stage'].sudo().create({'name': 'Temp Stage', 'sequence': 99})
        with self.assertRaises(AccessError):
            stage.with_user(self.user_pl_user).unlink()
            
        # User 2 (PL Manager) CAN unlink stages
        stage.with_user(self.user_pl_manager).unlink()
        
        # Company B User cannot see Company A's PL
        pl_comp_b_env = self.env['packing.list'].with_user(self.user_company_b)
        found_pls = pl_comp_b_env.search([('id', '=', pl_user_pl.id)])
        self.assertFalse(found_pls, "User in Company B should not see PL from Company A")
