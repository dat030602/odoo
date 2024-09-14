from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from .common import TestAccountAvataxCommon


@tagged("-at_install", "post_install")
class TestAccountAvalaraInternal(TestAccountAvataxCommon):
    def assertInvoice(self, invoice, test_exact_taxes=True):
        self.assertEqual(
            len(invoice.invoice_line_ids.tax_ids),
            0,
            "There should be no tax rate on the line."
        )

        self.assertRecordValues(invoice, [{
            'amount_total': 90.0,
            'amount_untaxed': 90.0,
            'amount_tax': 0.0,
        }])
        invoice.action_post()

        if test_exact_taxes:
            self.assertRecordValues(invoice, [{
                'amount_total': 96.54,
                'amount_untaxed': 90.0,
                'amount_tax': 6.54,
            }])
        else:
            for line in invoice.invoice_line_ids:
                product_name = line.product_id.display_name
                self.assertGreater(len(line.tax_ids), 0, "Line with %s did not get any taxes set." % product_name)

            self.assertGreater(invoice.amount_tax, 0.0, "Invoice has a tax_amount of 0.0.")

    def test_01_odoo_invoice(self):
        invoice, response = self._create_invoice_01_and_expected_response()
        with self._capture_request(return_value=response):
            self.assertInvoice(invoice, test_exact_taxes=True)

        # verify transactions are uncommitted
        with patch('odoo.addons.account_avatax.models.account_avatax.AccountAvatax._uncommit_avatax_transaction') as mocked_commit:
            invoice.button_draft()
            mocked_commit.assert_called()

    def test_integration_01_odoo_invoice(self):
        with self._skip_no_credentials():
            invoice, _ = self._create_invoice_01_and_expected_response()
            self.assertInvoice(invoice, test_exact_taxes=False)
            invoice.button_draft()

    def test_02_odoo_invoice(self):
        invoice, response = self._create_invoice_02_and_expected_response()
        with self._capture_request(return_value=response):
            self.assertInvoice(invoice)

        # verify transactions are uncommitted
        with patch('odoo.addons.account_avatax.models.account_avatax.AccountAvatax._uncommit_avatax_transaction') as mocked_commit:
            invoice.button_draft()
            mocked_commit.assert_called()

    def test_integration_02_odoo_invoice(self):
        with self._skip_no_credentials():
            invoice, _ = self._create_invoice_02_and_expected_response()
            self.assertInvoice(invoice, test_exact_taxes=False)
            invoice.button_draft()

    def test_01_odoo_refund(self):
        invoice, response = self._create_invoice_01_and_expected_response()

        with self._capture_request(return_value=response):
            invoice.action_post()

        move_reversal = self.env['account.move.reversal'] \
            .with_context(active_model='account.move', active_ids=invoice.ids) \
            .create({'refund_method': 'refund', 'journal_id': invoice.journal_id.id})
        refund = self.env['account.move'].browse(move_reversal.reverse_moves()['res_id'])

        # Amounts should be sent as negative for refunds:
        # https://developer.avalara.com/erp-integration-guide/sales-tax-badge/transactions/test-refunds/
        for line in refund._get_avatax_invoice_lines():
            if 'Discount' in line['description']:
                self.assertGreater(line['amount'], 0)
            else:
                self.assertLess(line['amount'], 0)


@tagged("-at_install", "post_install")
class TestAccountAvalaraSalesTaxAdministration(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/sales-tax-badge/"""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        res = super().setUpClass(chart_template_ref)
        cls.config = cls.env['res.config.settings'].create({})
        return res

    def test_disable_document_recording(self):
        """In order for this connector to be used in conjunction with other integrations to AvaTax,
        the user must be able to control which connector is used for recording documents to AvaTax.

        From a technical standpoint, simply use DocType: 'SalesOrder' on all calls
        and suppress any non-getTax calls (i.e. cancelTax, postTax).
        """
        self.env.company.avalara_commit = False
        invoice, response = self._create_invoice_01_and_expected_response()
        with self._capture_request(return_value=response), patch('odoo.addons.account_avatax.lib.avatax_client.AvataxClient.commit_transaction') as mocked_commit:
            invoice.action_post()
            mocked_commit.assert_not_called()

    def test_disable_avatax(self):
        """The user must have an option to turn on or off the AvaTax Calculation service
        independent of any other Avalara product or service.
        """
        self.fp_avatax.is_avatax = False
        with patch('odoo.addons.account_avatax.lib.avatax_client.AvataxClient.request') as mocked_request:
            self._create_invoice()
            mocked_request.assert_not_called()

    def test_integration_connect_button(self):
        """Test the connection to the AvaTax service and verify the AvaTax credentials."""
        with self._skip_no_credentials(), self.assertRaisesRegex(UserError, "'version'"):
            self.config.avatax_ping()
