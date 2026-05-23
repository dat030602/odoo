from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(AccountTestInvoicingCommon):

    def test_bank_statement_line_sale_order(self):
        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': '2019-01-01',
            'payment_ref': 'line_1',
            'amount': 100.0,
        })
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).sudo().create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                })
            ]
        })
        sale_order.action_confirm()

        downpayment = self.env['sale.advance.payment.inv'].with_context({
            'active_ids': [sale_order.id],
            'default_journal_id': self.company_data['default_journal_sale'].id,
            'bank_rec_widget_statement_line_id': statement_line.id,
        }).sudo().create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100.0,
        })
        downpayment.create_invoices()
        self.assertTrue(statement_line.is_reconciled)
