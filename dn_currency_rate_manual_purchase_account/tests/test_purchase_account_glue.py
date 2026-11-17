from odoo.tests.common import TransactionCase


class TestPurchaseAccountGlue(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'PO Vendor Test'})
        cls.currency_foreign = cls.env.ref('base.USD') if cls.company.currency_id != cls.env.ref('base.USD') else cls.env.ref('base.EUR')

    def test_01_prepare_invoice_custom_rate_propagation(self):
        """Test _prepare_invoice copies selected rate to vendor bill under custom mode."""
        rate_record = self.env['res.currency.rate'].create({
            'name': '2026-05-01 10:00:00',
            'rate': 1.48,
            'currency_id': self.currency_foreign.id,
            'company_id': self.company.id,
        })
        order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'currency_id': self.currency_foreign.id,
            'rate_mode': 'custom',
            'selected_rate_id': rate_record.id,
        })
        invoice_vals = order._prepare_invoice()
        self.assertEqual(invoice_vals.get('rate_mode'), 'custom')
        self.assertEqual(invoice_vals.get('selected_rate_id'), rate_record.id)
