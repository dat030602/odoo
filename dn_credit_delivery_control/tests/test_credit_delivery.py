from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError
from datetime import date, timedelta
from odoo import fields


class TestCreditDeliveryControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Groups
        cls.group_stock_user = cls.env.ref('stock.group_stock_user')
        cls.group_internal = cls.env.ref('base.group_user')
        cls.group_approver = cls.env.ref('dn_credit_sale_control.group_credit_approver')

        # Users
        cls.user_stock = cls.env['res.users'].create({
            'name': 'Stock User Test',
            'login': 'stock_user_credit_test',
            'email': 'stock_credit@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_stock_user.id])],
        })

        cls.user_approver = cls.env['res.users'].create({
            'name': 'Stock Approver Test',
            'login': 'approver_stock_credit_test',
            'email': 'approver_stock_credit@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_stock_user.id, cls.group_approver.id])],
        })

        # Partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Corporate Delivery Client',
            'company_id': cls.company.id,
            'credit_check_enabled': True,
            'max_overdue_days': 10,
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Industrial Sensor',
            'type': 'consu',
        })

        # Stock Locations & Picking Type
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.picking_type_out = cls.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('warehouse_id', '=', cls.warehouse.id)
        ], limit=1)

        cls.customer_location = cls.env['stock.location'].search([('usage', '=', 'customer')], limit=1)

    def _create_outgoing_picking(self, partner=None):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.picking_type_out.default_location_src_id.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': (partner or self.partner).id,
            'company_id': self.company.id,
            'move_ids': [(0, 0, {
                'description_picking': 'Test Delivery',
                'product_id': self.product.id,
                'product_uom': self.product.uom_id.id,
                'product_uom_qty': 5.0,
                'location_id': self.picking_type_out.default_location_src_id.id,
                'location_dest_id': self.customer_location.id,
                'company_id': self.company.id,
            })]
        })
        picking.action_confirm()
        picking.action_assign()
        return picking

    # ==========================================
    # 1. Delivery Validation Under Credit Checks
    # ==========================================

    def test_delivery_validation_normal(self):
        """When partner is not overdue, outgoing delivery validates without blocking."""
        picking = self._create_outgoing_picking()
        picking.button_validate()
        self.assertFalse(picking.is_credit_blocked)
        self.assertIn(picking.state, ('assigned', 'done'))

    def test_delivery_blocked_when_partner_overdue(self):
        """When partner has overdue invoices exceeding max_overdue_days, delivery is blocked."""
        # Create posted overdue invoice
        invoice = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'invoice_date': fields.Date.today() - timedelta(days=30),
            'invoice_date_due': fields.Date.today() - timedelta(days=20),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1.0,
                'price_unit': 1000.0,
            })]
        })
        invoice.action_post()

        self.partner._compute_overdue()
        self.assertTrue(self.partner.overdue_max_days > self.partner.max_overdue_days)

        picking = self._create_outgoing_picking()
        with self.assertRaises(UserError) as cm:
            picking.button_validate()

        self.assertIn("Delivery blocked: Max Overdue Days Exceeded for Delivery", str(cm.exception))

    def test_delivery_disabled_credit_check_allows_validation(self):
        """When credit_check_enabled is False on partner, delivery validates even if overdue."""
        self.partner.credit_check_enabled = False
        picking = self._create_outgoing_picking()
        picking.button_validate()
        self.assertFalse(picking.is_credit_blocked)

    # ==========================================
    # 2. Wizard Credit Release Workflow
    # ==========================================

    def test_credit_release_wizard_workflow(self):
        """Approver releases blocked delivery via wizard, generating audit log and allowing validation."""
        # Setup blocked picking
        picking = self._create_outgoing_picking()
        picking.write({
            'is_credit_blocked': True,
            'block_reason': 'Max Overdue Days Exceeded for Delivery'
        })

        # Approver triggers release delivery wizard
        action = picking.with_user(self.user_approver).action_release_delivery()
        self.assertEqual(action['res_model'], 'credit.release.wizard')

        # Approver confirms wizard
        wizard = self.env['credit.release.wizard'].with_user(self.user_approver).create({
            'picking_id': picking.id,
            'reason': 'Special customer VIP exemption granted',
        })
        wizard.action_confirm()

        # Picking should now be unblocked
        self.assertFalse(picking.is_credit_blocked)
        self.assertEqual(picking.credit_released_by, self.user_approver)
        self.assertTrue(picking.credit_released_date)

        # Audit log verification
        log = self.env['credit.release.log'].search([('picking_id', '=', picking.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.release_type, 'delivery')
        self.assertEqual(log.approved_by, self.user_approver)
        self.assertEqual(log.reason, 'Special customer VIP exemption granted')

        # Delivery can now be validated
        picking.button_validate()
        self.assertIn(picking.state, ('assigned', 'done'))

    # ==========================================
    # 3. Security & Access Rights
    # ==========================================

    def test_non_approver_cannot_release_delivery(self):
        """A regular stock user cannot release blocked delivery."""
        picking = self._create_outgoing_picking()
        picking.write({'is_credit_blocked': True, 'block_reason': 'Overdue'})

        with self.assertRaises(UserError) as cm:
            picking.with_user(self.user_stock).action_release_delivery()
        self.assertIn("Only Credit Approvers can release delivery", str(cm.exception))

        with self.assertRaises(AccessError):
            wizard = self.env['credit.release.wizard'].with_user(self.user_stock).create({
                'picking_id': picking.id,
                'reason': 'Unauthorized release attempt',
            })
            wizard.action_confirm()
