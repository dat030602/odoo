from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from odoo import fields


class TestAdvancedATP(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Security groups
        cls.group_alloc_user = cls.env.ref('dn_advanced_atp.group_allocation_user')
        cls.group_alloc_mgr = cls.env.ref('dn_advanced_atp.group_allocation_manager')
        cls.group_stock_user = cls.env.ref('stock.group_stock_user')
        cls.group_internal = cls.env.ref('base.group_user')

        # Users
        cls.user_mgr = cls.env['res.users'].create({
            'name': 'ATP Manager Test',
            'login': 'atp_mgr_test',
            'email': 'atp_mgr@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_stock_user.id, cls.group_alloc_mgr.id])],
        })

        cls.user_regular = cls.env['res.users'].create({
            'name': 'ATP Regular User Test',
            'login': 'atp_reg_test',
            'email': 'atp_reg@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_stock_user.id, cls.group_alloc_user.id])],
        })

        # Partner tags and Partners
        cls.tag_vip = cls.env['res.partner.category'].create({'name': 'Enterprise VIP'})
        cls.partner_vip = cls.env['res.partner'].create({
            'name': 'VIP Customer Corp',
            'company_id': cls.company.id,
            'category_id': [(6, 0, [cls.tag_vip.id])],
        })
        cls.partner_standard = cls.env['res.partner'].create({
            'name': 'Standard Retail Customer',
            'company_id': cls.company.id,
        })

        # Warehouse & Locations
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.customer_location = cls.env['stock.location'].search([('usage', '=', 'customer')], limit=1)

        # Storable Product
        cls.product = cls.env['product.product'].create({
            'name': 'High-End Router',
            'is_storable': True,
        })

        # Stock Quants: 10 units in stock
        cls.env['stock.quant']._update_available_quantity(
            cls.product,
            cls.warehouse.lot_stock_id,
            10.0
        )

        # Allocation Rule
        cls.rule = cls.env['allocation.rule'].create({
            'name': 'VIP Priority Allocation Rule',
            'company_id': cls.company.id,
            'warehouse_ids': [(6, 0, [cls.warehouse.id])],
            'protect_started_picking': True,
            'line_ids': [
                (0, 0, {'criterion': 'partner_tag', 'partner_tag_id': cls.tag_vip.id, 'weight': 100}),
                (0, 0, {'criterion': 'priority_flag', 'weight': 50}),
            ]
        })

    def _create_outgoing_picking(self, partner, qty, priority='0'):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': partner.id,
            'company_id': self.company.id,
            'priority': priority,
            'move_ids': [(0, 0, {
                'description_picking': 'Router Delivery',
                'product_id': self.product.id,
                'product_uom': self.product.uom_id.id,
                'product_uom_qty': qty,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.customer_location.id,
                'company_id': self.company.id,
            })]
        })
        picking.action_confirm()
        return picking

    # ==========================================
    # 1. Allocation Rule & Scoring Tests
    # ==========================================

    def test_allocation_rule_scoring(self):
        """Test scoring of moves based on partner tags and priority flags."""
        # VIP picking with normal priority -> score 100
        p_vip = self._create_outgoing_picking(self.partner_vip, 5.0, priority='0')
        move_vip = p_vip.move_ids[0]
        self.assertEqual(self.rule._score(move_vip), 100.0)

        # Standard partner with urgent priority ('1') -> score 50
        p_urgent = self._create_outgoing_picking(self.partner_standard, 5.0, priority='1')
        move_urgent = p_urgent.move_ids[0]
        self.assertEqual(self.rule._score(move_urgent), 50.0)

        # VIP partner with urgent priority ('1') -> score 150
        p_vip_urgent = self._create_outgoing_picking(self.partner_vip, 5.0, priority='1')
        move_vip_urgent = p_vip_urgent.move_ids[0]
        self.assertEqual(self.rule._score(move_vip_urgent), 150.0)

        # Standard partner with normal priority -> score 0
        p_standard = self._create_outgoing_picking(self.partner_standard, 5.0, priority='0')
        move_standard = p_standard.move_ids[0]
        self.assertEqual(self.rule._score(move_standard), 0.0)

    # ==========================================
    # 2. Allocation Run Simulation
    # ==========================================

    def test_allocation_run_simulate(self):
        """Simulate run calculates scores and candidate moves without applying stock changes."""
        p_standard = self._create_outgoing_picking(self.partner_standard, 6.0)
        p_vip = self._create_outgoing_picking(self.partner_vip, 8.0)

        run = self.env['allocation.run'].with_user(self.user_mgr).create({
            'rule_id': self.rule.id,
            'product_ids': [(6, 0, [self.product.id])],
            'warehouse_id': self.warehouse.id,
            'mode': 'simulate',
        })
        self.assertTrue(run.name.startswith('RUN/'))

        run.action_simulate()
        self.assertEqual(run.state, 'simulated')
        self.assertTrue(len(run.line_ids) >= 2)

        line_vip = run.line_ids.filtered(lambda l: l.partner_id == self.partner_vip)
        self.assertEqual(line_vip.score, 100.0)
        self.assertEqual(line_vip.demand_qty, 8.0)

    def test_allocation_run_empty_moves_safe(self):
        """Runs with no matching candidate moves complete safely without errors."""
        product_other = self.env['product.product'].create({
            'name': 'Unused Product',
            'is_storable': True,
        })
        run = self.env['allocation.run'].create({
            'rule_id': self.rule.id,
            'product_ids': [(6, 0, [product_other.id])],
            'mode': 'simulate',
        })
        run.action_simulate()
        self.assertEqual(run.state, 'simulated')
        self.assertEqual(len(run.line_ids), 0)

        run.action_apply()
        self.assertEqual(run.state, 'applied')
        self.assertEqual(len(run.line_ids), 0)

    # ==========================================
    # 3. Allocation Run Application & Re-prioritization
    # ==========================================

    def test_allocation_run_apply_reprioritizes_stock(self):
        """Applying allocation unreserves low priority orders and re-assigns to high priority VIP."""
        # Available stock: 10 units
        # First, standard customer reserves 10 units first
        p_standard = self._create_outgoing_picking(self.partner_standard, 10.0)
        p_standard.action_assign()
        move_std = p_standard.move_ids[0]
        self.assertEqual(move_std.quantity, 10.0)

        # Later, VIP customer orders 10 units, but stock is already taken
        p_vip = self._create_outgoing_picking(self.partner_vip, 10.0)
        p_vip.action_assign()
        move_vip = p_vip.move_ids[0]
        self.assertEqual(move_vip.quantity, 0.0) # Not reserved because stock ran out

        # Now execute ATP Allocation Run in 'apply' mode
        run = self.env['allocation.run'].with_user(self.user_mgr).create({
            'rule_id': self.rule.id,
            'product_ids': [(6, 0, [self.product.id])],
            'warehouse_id': self.warehouse.id,
            'mode': 'apply',
        })
        run.action_apply()

        self.assertEqual(run.state, 'applied')

        # VIP order (score 100) must now have the 10 units reserved
        self.assertEqual(move_vip.quantity, 10.0)

        # Standard order (score 0) must have 0 units reserved
        self.assertEqual(move_std.quantity, 0.0)

        # Verify allocation lines reflect delta
        line_vip = run.line_ids.filtered(lambda l: l.partner_id == self.partner_vip)
        self.assertEqual(line_vip.rank, 1)
        self.assertEqual(line_vip.reserved_after, 10.0)
        self.assertEqual(line_vip.delta_qty, 10.0)

        line_std = run.line_ids.filtered(lambda l: l.partner_id == self.partner_standard)
        self.assertEqual(line_std.rank, 2)
        self.assertEqual(line_std.reserved_after, 0.0)
        self.assertEqual(line_std.delta_qty, -10.0)

    # ==========================================
    # 4. Security & Permissions
    # ==========================================

    def test_security_access_rights(self):
        """Regular users cannot create allocation rules; managers have full CRUD."""
        # Regular user cannot create rule
        with self.assertRaises(AccessError):
            self.env['allocation.rule'].with_user(self.user_regular).create({
                'name': 'Unauthorized Rule',
            })

        # Regular user cannot create allocation run
        with self.assertRaises(AccessError):
            self.env['allocation.run'].with_user(self.user_regular).create({
                'rule_id': self.rule.id,
            })

        # Manager can create and delete rule
        mgr_rule = self.env['allocation.rule'].with_user(self.user_mgr).create({
            'name': 'Manager Created Rule',
        })
        self.assertTrue(mgr_rule.id)
        mgr_rule.unlink()
        self.assertFalse(mgr_rule.exists())
