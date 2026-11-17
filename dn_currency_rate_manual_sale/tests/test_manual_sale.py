from odoo.tests.common import TransactionCase


class TestManualSale(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Customer Test'})
        cls.currency_foreign = cls.env.ref('base.USD') if cls.company.currency_id != cls.env.ref('base.USD') else cls.env.ref('base.EUR')

        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Foreign Pricelist',
            'currency_id': cls.currency_foreign.id,
        })

    def test_01_sale_custom_rate(self):
        """Test selecting specific rate on sales order using custom mode."""
        rate_record = self.env['res.currency.rate'].create({
            'name': '2026-05-01 10:00:00',
            'rate': 1.40,
            'currency_id': self.currency_foreign.id,
            'company_id': self.company.id,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
            'picking_policy': 'direct',
            'rate_mode': 'custom',
            'selected_rate_id': rate_record.id,
        })
        comp_rate = self.company.currency_id._get_rates(self.company, '2026-05-01').get(self.company.currency_id.id, 1.0)
        expected = 1.40 / comp_rate
        self.assertAlmostEqual(order.currency_rate, expected)
