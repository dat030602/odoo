from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestMrpCostSimulation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # 1. Products setup
        cls.raw_wood = cls.env['product.product'].create({
            'name': 'Test Wood Plank',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 10.0,
        })
        cls.raw_screws = cls.env['product.product'].create({
            'name': 'Test Screws',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 1.0,
        })
        cls.raw_cushion = cls.env['product.product'].create({
            'name': 'Test Cushion',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 20.0,
        })
        cls.sub_frame = cls.env['product.product'].create({
            'name': 'Test Chair Frame',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 30.0,
        })
        cls.finished_chair = cls.env['product.product'].create({
            'name': 'Test Ergonomic Chair',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 70.0,
        })
        cls.byproduct_sawdust = cls.env['product.product'].create({
            'name': 'Test Sawdust',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 2.0,
        })

        # 2. Sub-BOM for Chair Frame: 2 Wood Planks + 4 Screws
        cls.bom_frame = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.sub_frame.product_tmpl_id.id,
            'product_id': cls.sub_frame.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_unit.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.raw_wood.id, 'product_qty': 2.0, 'product_uom_id': cls.uom_unit.id}),
                (0, 0, {'product_id': cls.raw_screws.id, 'product_qty': 4.0, 'product_uom_id': cls.uom_unit.id}),
            ]
        })

        # 3. Work Center & Operation
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Test Assembly Station',
            'costs_hour': 30.0,
        })

        # 4. Main BOM for Chair: 1 Frame + 1 Cushion + Byproduct + Operation
        cls.bom_chair = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.finished_chair.product_tmpl_id.id,
            'product_id': cls.finished_chair.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_unit.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.sub_frame.id, 'product_qty': 1.0, 'product_uom_id': cls.uom_unit.id}),
                (0, 0, {'product_id': cls.raw_cushion.id, 'product_qty': 1.0, 'product_uom_id': cls.uom_unit.id}),
            ],
            'byproduct_ids': [
                (0, 0, {
                    'product_id': cls.byproduct_sawdust.id,
                    'product_qty': 0.5,
                    'product_uom_id': cls.uom_unit.id,
                    'cost_share': 5.0,  # 5% allocated to byproduct
                })
            ],
            'operation_ids': [
                (0, 0, {
                    'name': 'Final Assembly',
                    'workcenter_id': cls.workcenter.id,
                    'time_cycle_manual': 30.0,  # 30 minutes = 0.5 hours -> $15
                })
            ]
        })

    def test_01_simulation_load_and_calculation(self):
        """Test loading BOM structure, material, labor, byproduct deduction."""
        sim = self.env['mrp.bom.simulation'].create({
            'bom_id': self.bom_chair.id,
            'description': 'Baseline Test Simulation',
            'product_qty': 1.0,
        })
        sim.action_load_from_bom()

        self.assertEqual(sim.state, 'calculated')
        # Sub-assembly exploded: 2 Wood + 4 Screws + 1 Cushion = 3 leaf lines
        self.assertEqual(len(sim.line_ids), 3)
        self.assertEqual(len(sim.operation_ids), 1)
        self.assertEqual(len(sim.byproduct_ids), 1)

        # Expected Material: Wood ($20) + Screws ($4) + Cushion ($20) = $44
        self.assertAlmostEqual(sim.total_material_cost, 44.0, places=2)

        # Expected Labor: 30 min / 60 * $30/hr = $15
        self.assertAlmostEqual(sim.total_labor_cost, 15.0, places=2)

        # Gross: $44 + $15 = $59. Byproduct share: 5% of $59 = $2.95
        self.assertAlmostEqual(sim.total_byproduct_deduction, 2.95, places=2)

        # Net unit simulated cost: $59 - $2.95 = $56.05
        self.assertAlmostEqual(sim.unit_cost_simulated, 56.05, places=2)

    def test_02_price_injection_and_scrap(self):
        """Test overriding material price, adding scrap %, and changing workcenter rate."""
        sim = self.env['mrp.bom.simulation'].create({
            'bom_id': self.bom_chair.id,
            'description': 'Price Shock Scenario',
            'product_qty': 1.0,
        })
        sim.action_load_from_bom()

        # Inject scrap 10% on cushion and increase cushion price from $20 to $25
        cushion_line = sim.line_ids.filtered(lambda l: l.product_id == self.raw_cushion)
        cushion_line.write({
            'scrap_rate': 10.0,
            'simulated_cost': 25.0,
        })
        self.assertAlmostEqual(cushion_line.qty_with_scrap, 1.1, places=2)
        self.assertAlmostEqual(cushion_line.subtotal_cost, 27.5, places=2)

        # Inject wage increase from $30 to $50 on operation
        op_line = sim.operation_ids[0]
        op_line.write({'simulated_costs_hour': 50.0})

        sim.action_recalculate()

        # Frame materials ($24) + Cushion ($27.5) = $51.5 materials
        self.assertAlmostEqual(sim.total_material_cost, 51.5, places=2)
        # Labor: 0.5 * $50 = $25
        self.assertAlmostEqual(sim.total_labor_cost, 25.0, places=2)
        # Gross = 51.5 + 25 = 76.5. Byproduct deduction: 5% of 76.5 = 3.825
        # Net = 76.5 - 3.825 = 72.675 -> rounded to currency 2 decimals = 72.68
        self.assertAlmostEqual(sim.unit_cost_simulated, 72.68, places=2)

    def test_03_versioning_and_application(self):
        """Test snapshot version creation and applying approved cost to product."""
        sim = self.env['mrp.bom.simulation'].create({
            'bom_id': self.bom_chair.id,
            'description': 'Budget V1',
            'product_qty': 1.0,
        })
        sim.action_load_from_bom()

        # Branch into V2 snapshot
        action_dict = sim.action_create_version()
        v2_sim = self.env['mrp.bom.simulation'].browse(action_dict['res_id'])
        self.assertEqual(v2_sim.version, 2)
        self.assertEqual(v2_sim.parent_simulation_id, sim)

        # Approve and Apply V2
        v2_sim.action_approve()
        self.assertEqual(v2_sim.state, 'approved')

        old_price = self.finished_chair.standard_price
        v2_sim.action_apply_simulation()
        self.assertEqual(v2_sim.state, 'applied')
        self.assertAlmostEqual(self.finished_chair.standard_price, v2_sim.unit_cost_simulated, places=2)
        self.assertNotEqual(self.finished_chair.standard_price, old_price)

    def test_04_bom_integration_and_lifecycle(self):
        """Test BOM smart buttons, actions, cancel and reset to draft."""
        # Test creation directly from BOM
        res = self.bom_chair.action_create_simulation()
        sim = self.env['mrp.bom.simulation'].browse(res['res_id'])
        self.assertEqual(sim.bom_id, self.bom_chair)
        self.assertEqual(sim.state, 'calculated')

        # Test simulation count on BOM
        self.bom_chair._compute_simulation_count()
        self.assertTrue(self.bom_chair.simulation_count >= 1)

        # Test view simulations action
        action = self.bom_chair.action_view_simulations()
        self.assertIn(('bom_id', '=', self.bom_chair.id), action['domain'])

        # Test cancel and reset to draft
        sim.action_cancel()
        self.assertEqual(sim.state, 'cancelled')
        sim.action_set_draft()
        self.assertEqual(sim.state, 'draft')

        # Test constraints on positive qty
        with self.assertRaises(Exception):
            self.env['mrp.bom.simulation'].create({
                'bom_id': self.bom_chair.id,
                'description': 'Zero Qty Test',
                'product_qty': 0.0,
            })

