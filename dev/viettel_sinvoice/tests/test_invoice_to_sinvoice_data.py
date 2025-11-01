# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
# from odoo.tests import tagged
from odoo.tests.common import tagged

@tagged('post_install', '-at_install')
class TestAccountSInvoiceViettel(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_3 = cls.setup_multi_currency_data({
            'name': "Umbrella",
            'symbol': '☂',
            'currency_unit_label': "Umbrella",
            'currency_subunit_label': "Broken Umbrella",
        }, rate2017=0.01)

        cls.payment_debit_account_id = cls.company_data['default_journal_bank'].payment_debit_account_id.copy()
        cls.payment_credit_account_id = cls.company_data['default_journal_bank'].payment_credit_account_id.copy()

        cls.custom_payment_method_in = cls.env['account.payment.method'].create({
            'name': 'custom_payment_method_in',
            'code': 'CUSTOMIN',
            'payment_type': 'inbound',
        })
        cls.manual_payment_method_in = cls.env.ref('account.account_payment_method_manual_in')

        cls.custom_payment_method_out = cls.env['account.payment.method'].create({
            'name': 'custom_payment_method_out',
            'code': 'CUSTOMOUT',
            'payment_type': 'outbound',
        })
        cls.manual_payment_method_out = cls.env.ref('account.account_payment_method_manual_out')

        cls.company_data['default_journal_bank'].write({
            'payment_debit_account_id': cls.payment_debit_account_id.id,
            'payment_credit_account_id': cls.payment_credit_account_id.id,
            'inbound_payment_method_ids': [(6, 0, (
                cls.manual_payment_method_in.id,
                cls.custom_payment_method_in.id,
            ))],
            'outbound_payment_method_ids': [(6, 0, (
                cls.env.ref('account.account_payment_method_manual_out').id,
                cls.custom_payment_method_out.id,
                cls.manual_payment_method_out.id,
            ))],
        })

        # Customer invoices sharing the same batch.
        cls.out_invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1000.0})],
        })
        cls.out_invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 2000.0})],
        })
        cls.out_invoice_3 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 12.01})],
        })
        cls.out_invoice_4 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 11.99})],
        })
        (cls.out_invoice_1 + cls.out_invoice_2 + cls.out_invoice_3 + cls.out_invoice_4).action_post()

        # Vendor bills, in_invoice_1 + in_invoice_2 are sharing the same batch but not in_invoice_3.
        cls.in_invoice_1 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1000.0})],
        })
        cls.in_invoice_2 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 2000.0})],
        })
        cls.in_invoice_3 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_b.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 3000.0})],
        })
        (cls.in_invoice_1 + cls.in_invoice_2 + cls.in_invoice_3).action_post()

    # def test_register_payment_single_batch_grouped_keep_open_lower_amount(self):
    #     print('=====================================')
    #     pass
    def test_register_payment_single_batch_grouped_writeoff_higher_amount_debit(self):
        ''' Pay 3100.0 with 'reconcile' as payment difference handling on two customer invoices (1000 + 2000). '''
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 3100.0,
            'group_payment': True,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'writeoff',
            'payment_method_id': self.custom_payment_method_in.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'payment_method_id': self.custom_payment_method_in.id,
        }])
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 15010.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3000.0,
                'reconciled': True,
            },
            # Writeoff line:
            {
                'debit': 0.0,
                'credit': 50.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -100.0,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 1550.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3100.0,
                'reconciled': False,
            },
        ])