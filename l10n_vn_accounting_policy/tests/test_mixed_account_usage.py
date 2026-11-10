# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMixedAccountUsage(AccountTestInvoicingCommon):
    """
    Unit test suite for Vietnamese accounting policy: Flexible mixed account usage.
    Verifies that accounts configured with vn_allow_mixed_usage=True bypass
    the document-type payable/receivable constraint while retaining off-balance
    and entry balance controls.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Normal accounts (vn_allow_mixed_usage = False)
        cls.account_payable_normal = cls.copy_account(
            cls.company_data['default_account_payable'],
            default={'name': 'Payable Normal', 'vn_allow_mixed_usage': False}
        )
        cls.account_receivable_normal = cls.copy_account(
            cls.company_data['default_account_receivable'],
            default={'name': 'Receivable Normal', 'vn_allow_mixed_usage': False}
        )

        # Mixed accounts simulating Vietnamese Chart of Accounts (vn_allow_mixed_usage = True)
        # E.g., Account 141 - Employee advances (liability_payable with mixed usage)
        cls.account_payable_mixed = cls.copy_account(
            cls.company_data['default_account_payable'],
            default={'name': 'Payable Mixed (TK 141)', 'vn_allow_mixed_usage': True}
        )
        # E.g., Account 131 - Customer prepayments / receivables with mixed usage
        cls.account_receivable_mixed = cls.copy_account(
            cls.company_data['default_account_receivable'],
            default={'name': 'Receivable Mixed (TK 131)', 'vn_allow_mixed_usage': True}
        )

        # Off-balance account for AC-4
        cls.account_off_balance = cls.env['account.account'].create({
            'name': 'Off-Balance Mixed',
            'code': 'OFFBAL01',
            'account_type': 'off_balance',
            'vn_allow_mixed_usage': True,
        })

        # Partner C for partner locking tests (AC-6 to AC-10)
        cls.partner_c = cls.partner_a.copy({'name': 'Partner C'})

    # -------------------------------------------------------------------------
    # AC-1: Normal payable and receivable accounts are strictly validated
    # -------------------------------------------------------------------------

    def test_ac1_normal_payable_on_sale_invoice_raises_user_error(self):
        """A normal payable account (flag disabled) cannot be used in a sale invoice."""
        with self.assertRaises(UserError):
            self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2026-01-01',
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Sale line with normal payable',
                        'account_id': self.account_payable_normal.id,
                        'quantity': 1.0,
                        'price_unit': 100.0,
                        'tax_ids': False,
                    }),
                ],
            })

    def test_ac1_normal_payable_on_vendor_bill_line_raises_user_error(self):
        """A normal payable account cannot be assigned to an invoice line without payment_term display_type."""
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Expense line',
                    'account_id': self.company_data['default_account_expense'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        with self.assertRaises(UserError):
            bill.invoice_line_ids[0].account_id = self.account_payable_normal

    def test_ac1_normal_receivable_on_vendor_bill_raises_user_error(self):
        """A normal receivable account cannot be used in a vendor bill."""
        with self.assertRaises(UserError):
            self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2026-01-01',
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Bill line with normal receivable',
                        'account_id': self.account_receivable_normal.id,
                        'quantity': 1.0,
                        'price_unit': 100.0,
                        'tax_ids': False,
                    }),
                ],
            })

    # -------------------------------------------------------------------------
    # AC-2: Mixed payable account (TK 141) can be posted on bills and invoices
    # -------------------------------------------------------------------------

    def test_ac2_mixed_payable_on_vendor_bill_post_success(self):
        """Mixed payable account (vn_allow_mixed_usage=True) can be posted on a vendor bill."""
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Expense line to be changed to TK 141',
                    'account_id': self.company_data['default_account_expense'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        bill.invoice_line_ids[0].account_id = self.account_payable_mixed
        bill.action_post()
        self.assertEqual(bill.state, 'posted', "Vendor bill using mixed payable account must post successfully.")

    def test_ac2_mixed_payable_on_customer_invoice_post_success(self):
        """Mixed payable account (vn_allow_mixed_usage=True) can be posted on a customer invoice."""
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Mixed payable on sale invoice',
                    'account_id': self.account_payable_mixed.id,
                    'quantity': 1.0,
                    'price_unit': 200.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted', "Customer invoice using mixed payable account must post successfully.")

    # -------------------------------------------------------------------------
    # AC-3: Mixed receivable account (TK 131) can be posted on vendor bills
    # -------------------------------------------------------------------------

    def test_ac3_mixed_receivable_on_vendor_bill_post_success(self):
        """Mixed receivable account (vn_allow_mixed_usage=True) can be posted on a vendor bill."""
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Prepayment offset line (TK 131)',
                    'account_id': self.account_receivable_mixed.id,
                    'quantity': 1.0,
                    'price_unit': 150.0,
                    'tax_ids': False,
                }),
            ],
        })
        bill.action_post()
        self.assertEqual(bill.state, 'posted', "Vendor bill using mixed receivable account must post successfully.")

    # -------------------------------------------------------------------------
    # AC-4: Off-balance constraint remains strictly enforced
    # -------------------------------------------------------------------------

    def test_ac4_off_balance_account_still_blocked(self):
        """Off-balance accounts mixed with regular balance accounts must raise UserError."""
        with self.assertRaises(UserError):
            self.env['account.move'].create({
                'move_type': 'entry',
                'line_ids': [
                    Command.create({
                        'name': 'Off-balance line',
                        'account_id': self.account_off_balance.id,
                        'debit': 100.0,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'name': 'Balance sheet line',
                        'account_id': self.account_payable_mixed.id,
                        'debit': 0.0,
                        'credit': 100.0,
                    }),
                ],
            })

    # -------------------------------------------------------------------------
    # AC-5: Balance constraint remains strictly enforced
    # -------------------------------------------------------------------------

    def test_ac5_unbalanced_entry_with_mixed_account_still_blocked(self):
        """Unbalanced journal entries with mixed accounts must raise UserError."""
        with self.assertRaises(UserError):
            self.env['account.move'].create({
                'move_type': 'entry',
                'line_ids': [
                    Command.create({
                        'name': 'Debit mixed line',
                        'account_id': self.account_payable_mixed.id,
                        'debit': 100.0,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'name': 'Unbalanced credit line',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'debit': 0.0,
                        'credit': 50.0,
                    }),
                ],
            })

    # -------------------------------------------------------------------------
    # AC-6 to AC-11: Line partner policy (vn_allow_different_partner)
    # -------------------------------------------------------------------------

    def test_ac6_line_partner_different_from_header_on_create_when_locked(self):
        """Header partner is partner_a, invoice line partner is partner_b with vn_allow_different_partner=True."""
        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'vn_allow_different_partner': True,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line with different partner',
                    'partner_id': self.partner_b.id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice_line = invoice_move.invoice_line_ids[0]
        self.assertTrue(invoice_move.vn_allow_different_partner)
        self.assertEqual(
            invoice_line.partner_id,
            self.partner_b,
            "Line partner should remain partner_b on create when vn_allow_different_partner is True."
        )

    def test_ac7_line_partner_update_allowed_in_draft_when_flagged(self):
        """Updating partner_id on a draft line is allowed when vn_allow_different_partner=True."""
        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'vn_allow_different_partner': True,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line with partner_b',
                    'partner_id': self.partner_b.id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice_line = invoice_move.invoice_line_ids[0]
        self.assertTrue(invoice_move.vn_allow_different_partner)
        self.assertEqual(invoice_move.state, 'draft')
        invoice_line.write({'partner_id': self.partner_c.id})
        self.assertEqual(
            invoice_line.partner_id,
            self.partner_c,
            "Line partner should be updated to partner_c in draft state when vn_allow_different_partner is True.",
        )

    def test_ac8_line_partner_update_allowed_when_unlocked(self):
        """Updating partner_id on a line is allowed when vn_allow_different_partner=False."""
        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'vn_allow_different_partner': False,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line to update partner',
                    'partner_id': self.partner_b.id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice_line = invoice_move.invoice_line_ids[0]
        self.assertFalse(invoice_move.vn_allow_different_partner)
        invoice_line.write({'partner_id': self.partner_c.id})
        self.assertEqual(
            invoice_line.partner_id,
            self.partner_c,
            "Updating partner_id on a line should succeed when vn_allow_different_partner is False."
        )

    def test_ac9_line_partner_write_identical_partner_allowed(self):
        """Writing identical partner_id or other fields on a line should not raise UserError when locked."""
        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'vn_allow_different_partner': True,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line with partner_b',
                    'partner_id': self.partner_b.id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice_line = invoice_move.invoice_line_ids[0]
        self.assertTrue(invoice_move.vn_allow_different_partner)
        invoice_line.write({
            'partner_id': invoice_line.partner_id.id,
            'name': 'Updated Description',
        })
        self.assertEqual(invoice_line.name, 'Updated Description')
        self.assertEqual(invoice_line.partner_id, self.partner_b)

    def test_ac10_move_header_partner_change_preserves_line_partner_when_locked(self):
        """Changing move header partner preserves line partners when vn_allow_different_partner=True."""
        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'vn_allow_different_partner': True,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line with partner_b',
                    'partner_id': self.partner_b.id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice_line = invoice_move.invoice_line_ids[0]
        self.assertTrue(invoice_move.vn_allow_different_partner)
        self.assertEqual(invoice_line.partner_id, self.partner_b)
        invoice_move.write({'partner_id': self.partner_c.id})
        self.assertEqual(invoice_move.partner_id, self.partner_c)
        self.assertEqual(
            invoice_line.partner_id,
            self.partner_b,
            "Line partner must not be overwritten when header partner changes if vn_allow_different_partner is True."
        )

    def test_ac11_post_invoice_preserves_different_line_partners(self):
        """Posting invoice preserves line partners when vn_allow_different_partner=True."""
        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'vn_allow_different_partner': True,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line with partner_b',
                    'partner_id': self.partner_b.id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice_line = invoice_move.invoice_line_ids[0]
        self.assertTrue(invoice_move.vn_allow_different_partner)
        self.assertEqual(invoice_line.partner_id, self.partner_b)

        invoice_move.action_post()

        self.assertEqual(invoice_move.state, 'posted', "Invoice should be successfully posted.")
        self.assertEqual(
            invoice_line.partner_id,
            self.partner_b,
            "Line partner should remain partner_b after invoice is posted."
        )

    def test_ac12_posted_line_partner_update_raises_user_error(self):
        """Updating partner_id on a posted invoice line raises UserError when vn_allow_different_partner=True."""
        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'vn_allow_different_partner': True,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line with partner_b',
                    'partner_id': self.partner_b.id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        invoice_line = invoice_move.invoice_line_ids[0]
        self.assertTrue(invoice_move.vn_allow_different_partner)
        invoice_move.action_post()
        self.assertEqual(invoice_move.state, 'posted', "Invoice should be successfully posted.")
        with self.assertRaisesRegex(UserError, "You cannot change the partner on journal items once posted."):
            invoice_line.write({'partner_id': self.partner_c.id})
