from odoo.tests.common import TransactionCase


class TestManualPurchase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Vendor Test'})
        cls.currency_foreign = cls.env.ref('base.USD') if cls.company.currency_id != cls.env.ref('base.USD') else cls.env.ref('base.EUR')

    def test_01_purchase_custom_rate(self):
        """Test selecting specific rate on purchase order using custom mode."""
        rate_record = self.env['res.currency.rate'].create({
            'name': '2026-05-01 10:00:00',
            'rate': 1.45,
            'currency_id': self.currency_foreign.id,
            'company_id': self.company.id,
        })
        order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'currency_id': self.currency_foreign.id,
            'rate_mode': 'custom',
            'selected_rate_id': rate_record.id,
        })
        comp_rate = self.company.currency_id._get_rates(self.company, '2026-05-01').get(self.company.currency_id.id, 1.0)
        expected = 1.45 / comp_rate
        self.assertAlmostEqual(order.currency_rate, expected)
