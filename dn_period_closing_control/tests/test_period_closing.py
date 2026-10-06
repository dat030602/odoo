from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError
from datetime import date, timedelta
from odoo import fields


class TestPeriodClosingControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'Second Test Company'})

        cls.group_manager = cls.env.ref('dn_period_closing_control.group_period_lock_manager')
        cls.group_internal = cls.env.ref('base.group_user')
        cls.group_sale_user = cls.env.ref('sales_team.group_sale_manager')

        # Test users
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Period Lock Manager Test',
            'login': 'user_mgr_test',
            'email': 'mgr@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id, cls.other_company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_sale_user.id, cls.group_manager.id])],
        })

        cls.user_employee = cls.env['res.users'].create({
            'name': 'Regular Employee Test',
            'login': 'user_emp_test',
            'email': 'emp@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_sale_user.id])],
        })

        # Test partner and product
        cls.partner = cls.env['res.partner'].create({
            'name': 'Customer Test Corp',
            'company_id': cls.company.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Inventory Product',
            'type': 'consu',
        })

        # Stock locations
        cls.stock_location = cls.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', 'in', [cls.company.id, False])
        ], limit=1)
        cls.customer_location = cls.env['stock.location'].search([
            ('usage', '=', 'customer')
        ], limit=1)

        # Baseline dates
        cls.locked_date = date(2026, 1, 10)
        cls.lock_boundary_date = date(2026, 1, 15)
        cls.unlocked_date = date(2026, 2, 1)

    def _create_lock(self, company, scope, lock_date, applies_to_admin=True, active=True):
        return self.env['period.lock'].create({
            'company_id': company.id,
            'active': active,
            'line_ids': [(0, 0, {
                'scope': scope,
                'lock_date': lock_date,
                'applies_to_admin': applies_to_admin,
            })]
        })

    # ==========================================
    # 1. Period Lock Model & CRUD Tests
    # ==========================================

    def test_period_lock_creation_and_cascade(self):
        """Test Period Lock and lines creation, defaults, and cascade delete."""
        lock = self.env['period.lock'].create({
            'company_id': self.company.id,
            'active': True,
            'line_ids': [
                (0, 0, {'scope': 'sale', 'lock_date': self.lock_boundary_date, 'applies_to_admin': True}),
                (0, 0, {'scope': 'purchase', 'lock_date': self.lock_boundary_date, 'applies_to_admin': False}),
                (0, 0, {'scope': 'inventory', 'lock_date': self.lock_boundary_date, 'applies_to_admin': True}),
                (0, 0, {'scope': 'expense', 'lock_date': self.lock_boundary_date, 'applies_to_admin': True}),
            ]
        })
        self.assertEqual(len(lock.line_ids), 4)
        line_ids = lock.line_ids.ids

        # Deleting the header should cascade delete lines
        lock.unlink()
        remaining_lines = self.env['period.lock.line'].search([('id', 'in', line_ids)])
        self.assertFalse(remaining_lines)

    # ==========================================
    # 2. Sale Order Lock Enforcement Tests
    # ==========================================

    def test_sale_order_create_locked_raises_error(self):
        """Creating a sale.order in a locked period must raise UserError."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        with self.assertRaises(UserError) as cm:
            self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'company_id': self.company.id,
                'date_order': self.locked_date,
            })
        self.assertIn('Operation in locked period for sale', str(cm.exception))

    def test_sale_order_create_unlocked_succeeds(self):
        """Creating a sale.order outside the locked period must succeed."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.unlocked_date,
        })
        self.assertTrue(order.id)

    def test_sale_order_write_locked_record_raises_error(self):
        """Modifying an existing sale.order with date in locked period must raise UserError."""
        # Create initially outside lock
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.unlocked_date,
        })
        # Advance lock date so existing order falls into locked period
        self._create_lock(self.company, 'sale', date(2026, 2, 10), applies_to_admin=True)

        with self.assertRaises(UserError) as cm:
            order.write({'client_order_ref': 'PO-TEST-123'})
        self.assertIn('Operation in locked period for sale', str(cm.exception))

    def test_sale_order_write_backdate_into_lock_raises_error(self):
        """Backdating an unlocked order into a locked period must raise UserError."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.unlocked_date,
        })

        with self.assertRaises(UserError) as cm:
            order.write({'date_order': self.locked_date})
        self.assertIn('Operation in locked period for sale', str(cm.exception))

    def test_sale_order_unlink_locked_raises_error(self):
        """Unlinking a sale.order in a locked period must raise UserError."""
        # Create with bypass context
        order = self.env['sale.order'].with_context(bypass_period_lock=True).create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        with self.assertRaises(UserError) as cm:
            order.with_context(bypass_period_lock=False).unlink()
        self.assertIn('Operation in locked period for sale', str(cm.exception))

    def test_sale_order_unlink_unlocked_succeeds(self):
        """Unlinking a sale.order outside a locked period must succeed."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.unlocked_date,
        })
        order.unlink()
        self.assertFalse(order.exists())

    # ==========================================
    # 3. Stock Move Lock Enforcement Tests
    # ==========================================

    def test_stock_move_create_locked_raises_error(self):
        """Creating a stock.move in locked inventory period must raise UserError."""
        self._create_lock(self.company, 'inventory', self.lock_boundary_date, applies_to_admin=True)

        with self.assertRaises(UserError) as cm:
            self.env['stock.move'].create({
                'description_picking': 'Test Move',
                'product_id': self.product.id,
                'product_uom': self.product.uom_id.id,
                'product_uom_qty': 10.0,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'company_id': self.company.id,
                'date': self.locked_date,
            })
        self.assertIn('Operation in locked period for inventory', str(cm.exception))

    def test_stock_move_create_unlocked_succeeds(self):
        """Creating a stock.move outside locked inventory period must succeed."""
        self._create_lock(self.company, 'inventory', self.lock_boundary_date, applies_to_admin=True)

        move = self.env['stock.move'].create({
            'description_picking': 'Test Move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 10.0,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'company_id': self.company.id,
            'date': self.unlocked_date,
        })
        self.assertTrue(move.id)

    def test_stock_move_write_and_unlink_locked_raises_error(self):
        """Modifying or unlinking a stock.move in locked period must raise UserError."""
        move = self.env['stock.move'].with_context(bypass_period_lock=True).create({
            'description_picking': 'Locked Move',
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 5.0,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'company_id': self.company.id,
            'date': self.locked_date,
        })
        self._create_lock(self.company, 'inventory', self.lock_boundary_date, applies_to_admin=True)

        move_locked = move.with_context(bypass_period_lock=False)
        with self.assertRaises(UserError):
            move_locked.write({'product_uom_qty': 15.0})

        with self.assertRaises(UserError):
            move_locked.unlink()

    # ==========================================
    # 4. Bypass & Admin Exemption Tests
    # ==========================================

    def test_bypass_period_lock_context(self):
        """The context flag 'bypass_period_lock' must bypass all lock checks."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        order = self.env['sale.order'].with_context(bypass_period_lock=True).create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })
        self.assertTrue(order.id)

        order.with_context(bypass_period_lock=True).write({'client_order_ref': 'BYPASS-OK'})
        self.assertEqual(order.client_order_ref, 'BYPASS-OK')

        order.with_context(bypass_period_lock=True).unlink()
        self.assertFalse(order.exists())

    def test_applies_to_admin_behavior(self):
        """When applies_to_admin is False, admin bypasses lock while employee is blocked."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=False)

        # Admin user creating in locked period should succeed
        admin_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })
        self.assertTrue(admin_order.id)

        # Regular employee creating in locked period must fail
        with self.assertRaises(UserError):
            self.env['sale.order'].with_user(self.user_employee).create({
                'partner_id': self.partner.id,
                'company_id': self.company.id,
                'date_order': self.locked_date,
            })

    def test_inactive_lock_does_not_block(self):
        """Inactive period locks (active=False) must not block operations."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, active=False)

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })
        self.assertTrue(order.id)

    def test_different_company_lock_isolation(self):
        """Locks configured on Company B must not block Company A."""
        self._create_lock(self.other_company, 'sale', self.lock_boundary_date)

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })
        self.assertTrue(order.id)

    # ==========================================
    # 5. Unlock Request Workflow & Expiry Tests
    # ==========================================

    def test_unlock_request_full_lifecycle(self):
        """Test draft -> submitted -> approved -> revoked workflow and activity scheduling."""
        req = self.env['period.unlock.request'].with_user(self.user_employee).create({
            'scope': 'sale',
            'reason': 'Need to post backdated sale invoice adjustment',
        })
        self.assertEqual(req.state, 'draft')
        self.assertTrue(req.name.startswith('UR/'))

        # Submit request
        req.action_submit()
        self.assertEqual(req.state, 'submitted')

        # Approve request by manager
        req.with_user(self.user_manager).action_approve()
        self.assertEqual(req.state, 'approved')
        self.assertEqual(req.approver_id, self.user_manager)
        self.assertTrue(req.grant_start)
        self.assertTrue(req.grant_end)
        self.assertTrue(req.grant_end > req.grant_start)

        # Revoke request
        req.with_user(self.user_manager).action_revoke()
        self.assertEqual(req.state, 'revoked')

    def test_unlock_request_reject(self):
        """Test rejecting an unlock request."""
        req = self.env['period.unlock.request'].with_user(self.user_employee).create({
            'scope': 'inventory',
            'reason': 'Adjust stock count',
        })
        req.action_submit()
        req.with_user(self.user_manager).action_reject()
        self.assertEqual(req.state, 'rejected')

    def test_cron_expire_requests(self):
        """Test cron job auto-expiring approved requests when grant_end passes."""
        req = self.env['period.unlock.request'].with_user(self.user_employee).create({
            'scope': 'sale',
            'reason': 'Testing expiration',
        })
        req.action_submit()
        req.with_user(self.user_manager).action_approve()

        # Artificially set grant_end to the past
        past_time = fields.Datetime.now() - timedelta(minutes=10)
        req.sudo().write({'grant_end': past_time})

        # Run cron
        self.env['period.unlock.request']._cron_expire_requests()
        self.assertEqual(req.state, 'expired')

    # ==========================================
    # 6. Operations Under Active Grant & Audit Logs
    # ==========================================

    def test_general_unlock_grant_permits_operations_and_creates_logs(self):
        """An approved general unlock grant allows operations and records audit logs."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        # User submits and manager approves general sale grant
        req = self.env['period.unlock.request'].with_user(self.user_employee).create({
            'scope': 'sale',
            'reason': 'Urgent correction required',
        })
        req.action_submit()
        req.with_user(self.user_manager).action_approve()

        # Employee creates sale order in locked period -> Allowed under grant
        order = self.env['sale.order'].with_user(self.user_employee).create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })
        self.assertTrue(order.id)

        # Check create audit log
        create_log = self.env['period.unlock.log'].search([
            ('request_id', '=', req.id),
            ('operation', '=', 'create'),
        ])
        self.assertTrue(create_log)
        self.assertEqual(create_log.user_id, self.user_employee)

        # Employee writes to sale order -> Allowed and logged
        order.with_user(self.user_employee).write({'client_order_ref': 'MODIFIED-BY-GRANT'})
        write_log = self.env['period.unlock.log'].search([
            ('request_id', '=', req.id),
            ('operation', '=', 'write'),
            ('res_id', '=', order.id),
        ])
        self.assertTrue(write_log)

        # Employee unlinks sale order -> Allowed and logged
        order.with_user(self.user_employee).unlink()
        unlink_log = self.env['period.unlock.log'].search([
            ('request_id', '=', req.id),
            ('operation', '=', 'unlink'),
        ])
        self.assertTrue(unlink_log)

    def test_specific_record_grant_permits_only_target_record(self):
        """An unlock grant scoped to a specific record allows that record but blocks others."""
        self._create_lock(self.company, 'sale', self.lock_boundary_date, applies_to_admin=True)

        # Create two locked orders using bypass
        order_target = self.env['sale.order'].with_context(bypass_period_lock=True).create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })
        order_other = self.env['sale.order'].with_context(bypass_period_lock=True).create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': self.locked_date,
        })

        # Request grant specific to order_target only
        req = self.env['period.unlock.request'].with_user(self.user_employee).create({
            'scope': 'sale',
            'res_model': 'sale.order',
            'res_id': order_target.id,
            'reason': 'Correction for order_target only',
        })
        req.action_submit()
        req.with_user(self.user_manager).action_approve()

        # Writing to target order succeeds
        order_target.with_user(self.user_employee).with_context(bypass_period_lock=False).write({'client_order_ref': 'SPECIFIC-OK'})
        self.assertEqual(order_target.client_order_ref, 'SPECIFIC-OK')

        # Writing to other order fails
        with self.assertRaises(UserError):
            order_other.with_user(self.user_employee).with_context(bypass_period_lock=False).write({'client_order_ref': 'SHOULD-FAIL'})

    # ==========================================
    # 7. Security & Access Rights Tests
    # ==========================================

    def test_security_access_rights(self):
        """Regular users cannot manage Period Locks; only managers can."""
        # Employee cannot create period.lock
        with self.assertRaises(AccessError):
            self.env['period.lock'].with_user(self.user_employee).create({
                'company_id': self.company.id,
                'line_ids': [(0, 0, {'scope': 'sale', 'lock_date': self.lock_boundary_date})],
            })

        # Manager can create period.lock
        lock = self.env['period.lock'].with_user(self.user_manager).create({
            'company_id': self.company.id,
            'line_ids': [(0, 0, {'scope': 'sale', 'lock_date': self.lock_boundary_date})],
        })
        self.assertTrue(lock.id)

    def test_non_manager_cannot_approve_request(self):
        """A regular user without lock manager rights cannot approve unlock requests."""
        req = self.env['period.unlock.request'].with_user(self.user_employee).create({
            'scope': 'sale',
            'reason': 'Trying to self approve',
        })
        req.action_submit()
        with self.assertRaises(UserError):
            req.with_user(self.user_employee).action_approve()
