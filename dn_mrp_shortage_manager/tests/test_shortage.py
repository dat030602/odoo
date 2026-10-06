from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo import fields


class TestMrpShortageManager(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Users
        cls.group_mrp_user = cls.env.ref('mrp.group_mrp_user')
        cls.group_internal = cls.env.ref('base.group_user')
        cls.user_mrp = cls.env['res.users'].create({
            'name': 'MRP Planner Test',
            'login': 'mrp_planner_test',
            'email': 'planner@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_mrp_user.id])],
        })

        # Partners
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Raw Material Vendor Inc',
            'company_id': cls.company.id,
        })

        # Products
        cls.component_a = cls.env['product.product'].create({
            'name': 'Steel Sheet Component A',
            'is_storable': True,
            'standard_price': 25.0,
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor.id,
                'min_qty': 1.0,
                'price': 25.0,
            })]
        })

        cls.component_b_no_vendor = cls.env['product.product'].create({
            'name': 'Special Screw Component B',
            'is_storable': True,
            'standard_price': 5.0,
        })

        cls.finished_good = cls.env['product.product'].create({
            'name': 'Industrial Cabinet',
            'is_storable': True,
        })

        # Warehouse and picking type
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.picking_type = cls.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id', '=', cls.warehouse.id)
        ], limit=1)

        # BOM
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.finished_good.product_tmpl_id.id,
            'product_id': cls.finished_good.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.component_a.id, 'product_qty': 2.0}),
                (0, 0, {'product_id': cls.component_b_no_vendor.id, 'product_qty': 4.0}),
            ]
        })

    def _create_mo(self, qty=1.0, date_start=None):
        mo = self.env['mrp.production'].create({
            'product_id': self.finished_good.id,
            'bom_id': self.bom.id,
            'product_qty': qty,
            'product_uom_id': self.finished_good.uom_id.id,
            'company_id': self.company.id,
            'date_start': date_start or fields.Datetime.now(),
        })
        mo.action_confirm()
        return mo

    # ==========================================
    # 1. MO Readiness and Shortage Count Computes
    # ==========================================

    def test_mo_readiness_and_shortage_count(self):
        """Test readiness percentage and shortage count on mrp.production."""
        mo = self._create_mo(qty=2.0)
        # Component A: demand 4.0, Component B: demand 8.0, total demand = 12.0
        # Initially quantity (reserved) is 0
        mo._compute_readiness()
        mo._compute_shortage_count()
        self.assertEqual(mo.readiness_percentage, 0.0)
        self.assertEqual(mo.shortage_line_count, 2)

        # Partially reserve Component A (2 out of 4)
        move_a = mo.move_raw_ids.filtered(lambda m: m.product_id == self.component_a)
        move_a.quantity = 2.0

        mo._compute_readiness()
        mo._compute_shortage_count()
        # 2 reserved out of 12 demand -> (2 / 12) * 100 = 16.666%
        self.assertAlmostEqual(mo.readiness_percentage, 16.67, places=1)
        self.assertEqual(mo.shortage_line_count, 2)

        # Fully reserve Component A (4 out of 4) and Component B (8 out of 8)
        move_a.quantity = 4.0
        move_b = mo.move_raw_ids.filtered(lambda m: m.product_id == self.component_b_no_vendor)
        move_b.quantity = 8.0

        mo._compute_readiness()
        mo._compute_shortage_count()
        self.assertEqual(mo.readiness_percentage, 100.0)
        self.assertEqual(mo.shortage_line_count, 0)

    def test_mo_readiness_no_raw_moves(self):
        """Test readiness when an MO has no components (demand = 0)."""
        product_no_bom = self.env['product.product'].create({
            'name': 'Standalone Product Without BOM',
            'is_storable': True,
        })
        mo_empty = self.env['mrp.production'].create({
            'product_id': product_no_bom.id,
            'product_qty': 1.0,
            'product_uom_id': product_no_bom.uom_id.id,
            'company_id': self.company.id,
        })
        mo_empty._compute_readiness()
        self.assertEqual(mo_empty.readiness_percentage, 100.0)

    # ==========================================
    # 2. Shortage Dashboard Computation
    # ==========================================

    def test_shortage_dashboard_computation(self):
        """Test shortage dashboard computes shortages across multiple MOs."""
        mo1 = self._create_mo(qty=1.0, date_start=datetime(2026, 3, 10, 8, 0))
        mo2 = self._create_mo(qty=2.0, date_start=datetime(2026, 3, 15, 8, 0))

        dashboard = self.env['mrp.shortage.dashboard'].with_user(self.user_mrp).create({
            'warehouse_id': self.warehouse.id,
            'include_forecast_receipts': True,
        })

        action = dashboard.action_compute()
        self.assertEqual(action['res_id'], dashboard.id)

        line_a = dashboard.line_ids.filtered(lambda l: l.product_id == self.component_a)
        self.assertTrue(line_a)
        # Component A: 2 (mo1) + 4 (mo2) = 6.0 demand
        self.assertEqual(line_a.required_qty, 6.0)
        self.assertEqual(line_a.shortage_qty, 6.0)
        self.assertEqual(line_a.blocked_mo_count, 2)
        self.assertEqual(set(line_a.production_ids.ids), {mo1.id, mo2.id})
        self.assertEqual(line_a.earliest_mo_date, datetime(2026, 3, 10, 8, 0))

        line_b = dashboard.line_ids.filtered(lambda l: l.product_id == self.component_b_no_vendor)
        self.assertTrue(line_b)
        self.assertEqual(line_b.required_qty, 12.0)
        self.assertEqual(line_b.shortage_qty, 12.0)

    def test_shortage_dashboard_forecast_purchase(self):
        """Test PO covering shortages sets next_eta and covered_by_po."""
        mo = self._create_mo(qty=1.0)
        # Component A shortage is 2.0

        # Create PO for Component A
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'company_id': self.company.id,
            'order_line': [(0, 0, {
                'product_id': self.component_a.id,
                'product_qty': 10.0,
                'price_unit': 25.0,
                'date_planned': fields.Datetime.now() + timedelta(days=2),
            })]
        })
        po.button_confirm()

        dashboard = self.env['mrp.shortage.dashboard'].create({
            'include_forecast_receipts': True,
        })
        dashboard.action_compute()

        line_a = dashboard.line_ids.filtered(lambda l: l.product_id == self.component_a)
        self.assertTrue(line_a.covered_by_po)
        self.assertEqual(line_a.incoming_qty, 10.0)
        self.assertTrue(line_a.next_eta)

    def test_shortage_dashboard_date_and_warehouse_filters(self):
        """Test filtering shortages by date range and warehouse."""
        date_target = datetime(2026, 4, 10, 8, 0)
        mo_in_range = self._create_mo(qty=1.0, date_start=date_target)
        mo_out_range = self._create_mo(qty=1.0, date_start=datetime(2026, 5, 20, 8, 0))

        dashboard = self.env['mrp.shortage.dashboard'].create({
            'date_from': datetime(2026, 4, 1),
            'date_to': datetime(2026, 4, 30),
            'warehouse_id': self.warehouse.id,
        })
        dashboard.action_compute()

        line_a = dashboard.line_ids.filtered(lambda l: l.product_id == self.component_a)
        # Only mo_in_range should be included
        self.assertEqual(line_a.required_qty, 2.0)
        self.assertEqual(line_a.blocked_mo_count, 1)
        self.assertIn(mo_in_range.id, line_a.production_ids.ids)
        self.assertNotIn(mo_out_range.id, line_a.production_ids.ids)

    # ==========================================
    # 3. Create RFQ from Shortage Line
    # ==========================================

    def test_action_create_rfq_success(self):
        """Test creating RFQ directly from shortage line when vendor exists."""
        self._create_mo(qty=1.0)
        dashboard = self.env['mrp.shortage.dashboard'].create({})
        dashboard.action_compute()

        line_a = dashboard.line_ids.filtered(lambda l: l.product_id == self.component_a)
        action = line_a.action_create_rfq()

        self.assertEqual(action['res_model'], 'purchase.order')
        po = self.env['purchase.order'].browse(action['res_id'])
        self.assertEqual(po.partner_id, self.vendor)
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line.product_id, self.component_a)
        self.assertEqual(po.order_line.product_qty, line_a.shortage_qty)

    def test_action_create_rfq_no_vendor_raises_user_error(self):
        """Test creating RFQ from shortage line raises UserError if no vendor is configured."""
        self._create_mo(qty=1.0)
        dashboard = self.env['mrp.shortage.dashboard'].create({})
        dashboard.action_compute()

        line_b = dashboard.line_ids.filtered(lambda l: l.product_id == self.component_b_no_vendor)
        with self.assertRaises(UserError) as cm:
            line_b.action_create_rfq()
        self.assertIn("No vendor defined for product", str(cm.exception))
