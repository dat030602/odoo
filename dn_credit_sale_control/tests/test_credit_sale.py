from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date, timedelta
from odoo import fields


class TestCreditSaleControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Security groups
        cls.group_sale_user = cls.env.ref('sales_team.group_sale_manager')
        cls.group_internal = cls.env.ref('base.group_user')
        cls.group_approver = cls.env.ref('dn_credit_sale_control.group_credit_approver')
        cls.group_viewer = cls.env.ref('dn_credit_sale_control.group_credit_viewer')

        # Test users
        cls.user_sales = cls.env['res.users'].create({
            'name': 'Sales User Test',
            'login': 'sales_user_credit_test',
            'email': 'sales_credit@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_sale_user.id])],
        })

        cls.user_approver = cls.env['res.users'].create({
            'name': 'Credit Approver Test',
            'login': 'approver_credit_test',
            'email': 'approver_credit@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_sale_user.id, cls.group_approver.id])],
        })

        # Partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Corporate Client A',
            'company_id': cls.company.id,
            'credit_check_enabled': True,
            'credit_limit_amount': 1000.0,
            'grace_amount': 100.0,
            'max_overdue_days': 15,
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Server Hardware Unit',
            'type': 'consu',
            'list_price': 500.0,
        })

    def _create_so(self, partner=None, qty=1.0, price_unit=500.0):
        return self.env['sale.order'].create({
            'partner_id': (partner or self.partner).id,
            'company_id': self.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': qty,
                'price_unit': price_unit,
            })]
        })

    # ==========================================
    # 1. Partner Credit Exposure & Overdue Computes
    # ==========================================

    def test_partner_credit_check_logic(self):
        """Test _credit_check evaluation for disabled check, limits, and grace."""
        partner = self.partner
        so = self._create_so(qty=1.0, price_unit=500.0)

        # 1. Normal order within limit: exposure 500 <= limit 1000
        ok, reason = partner._credit_check(so)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

        # 2. Exceeding limit: qty=3.0 -> amount 1500. Grace 100 -> 1500 - 100 = 1400 > 1000
        so_large = self._create_so(qty=3.0, price_unit=500.0)
        ok, reason = partner._credit_check(so_large)
        self.assertFalse(ok)
        self.assertEqual(reason, "Credit Limit Exceeded")

        # 3. Disabled credit check ignores limit
        partner.credit_check_enabled = False
        ok, reason = partner._credit_check(so_large)
        self.assertTrue(ok)
        partner.credit_check_enabled = True

    def test_partner_credit_check_for_delivery(self):
        """Test _credit_check_for_delivery checks overdue status."""
        partner = self.partner
        # Normal check passes
        ok, reason = partner._credit_check_for_delivery(None)
        self.assertTrue(ok)

        # Disabled credit check passes
        partner.credit_check_enabled = False
        ok, reason = partner._credit_check_for_delivery(None)
        self.assertTrue(ok)

    # ==========================================
    # 2. Sale Order Confirmation & Credit Hold
    # ==========================================

    def test_sale_order_confirm_within_limit(self):
        """An order within the credit limit confirms directly to 'sale' state."""
        so = self._create_so(qty=1.0, price_unit=500.0)
        so.action_confirm()
        self.assertEqual(so.state, 'sale')

    def test_sale_order_confirm_exceeding_limit_holds_order(self):
        """An order exceeding the credit limit transitions to 'credit_hold'."""
        so = self._create_so(qty=3.0, price_unit=500.0) # total 1500 > limit 1000 + grace 100
        so.action_confirm()
        self.assertEqual(so.state, 'credit_hold')
        self.assertEqual(so.credit_block_reason, "Credit Limit Exceeded")
        self.assertTrue(so.credit_exposure_snapshot >= 0)

    def test_sale_order_confirm_with_skip_credit_check_context(self):
        """Using skip_credit_check context flag bypasses credit hold."""
        so = self._create_so(qty=3.0, price_unit=500.0)
        so.with_context(skip_credit_check=True).action_confirm()
        self.assertEqual(so.state, 'sale')

    # ==========================================
    # 3. Credit Approval & Rejection Workflow
    # ==========================================

    def test_credit_approval_workflow_and_audit_log(self):
        """Approving credit hold confirms SO, logs release, and sets approval tracking."""
        so = self._create_so(qty=3.0, price_unit=500.0)
        so.action_confirm()
        self.assertEqual(so.state, 'credit_hold')

        # Approver approves credit
        so.with_user(self.user_approver).action_approve_credit()

        # SO should now be confirmed
        self.assertEqual(so.state, 'sale')
        self.assertEqual(so.credit_approved_by, self.user_approver)
        self.assertTrue(so.credit_approved_date)

        # Audit log verification
        log = self.env['credit.release.log'].search([('sale_order_id', '=', so.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.release_type, 'sale_order')
        self.assertEqual(log.partner_id, self.partner)
        self.assertEqual(log.approved_by, self.user_approver)
        self.assertEqual(log.limit, 1000.0)

    def test_credit_rejection_workflow(self):
        """Rejecting credit hold cancels the sales order."""
        so = self._create_so(qty=3.0, price_unit=500.0)
        so.action_confirm()
        self.assertEqual(so.state, 'credit_hold')

        # Approver rejects credit
        so.with_user(self.user_approver).action_reject_credit()
        self.assertEqual(so.state, 'cancel')

    # ==========================================
    # 4. Security & Permissions
    # ==========================================

    def test_non_approver_cannot_approve_or_reject_credit(self):
        """A salesperson without credit approver group cannot approve or reject credit hold."""
        so = self._create_so(qty=3.0, price_unit=500.0)
        so.action_confirm()
        self.assertEqual(so.state, 'credit_hold')

        # Non-approver attempts to approve
        with self.assertRaises(UserError) as cm:
            so.with_user(self.user_sales).action_approve_credit()
        self.assertIn("Only Credit Approvers can approve", str(cm.exception))

        # Non-approver attempts to reject
        with self.assertRaises(UserError) as cm:
            so.with_user(self.user_sales).action_reject_credit()
        self.assertIn("Only Credit Approvers can approve or reject", str(cm.exception))
