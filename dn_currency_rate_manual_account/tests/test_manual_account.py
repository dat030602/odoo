from odoo.tests.common import TransactionCase


class TestManualAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency_usd = cls.env.ref('base.USD')
        # Ensure company currency is different from USD if needed
        if cls.company.currency_id == cls.currency_usd:
            cls.currency_foreign = cls.env.ref('base.EUR')
        else:
            cls.currency_foreign = cls.currency_usd

        cls.partner = cls.env['res.partner'].create({'name': 'Customer Test'})

    def test_01_account_custom_rate(self):
        """Test selecting specific rate on invoice using custom mode."""
        rate_record = self.env['res.currency.rate'].create({
            'name': '2026-05-01 10:00:00',
            'rate': 1.35,
            'currency_id': self.currency_foreign.id,
            'company_id': self.company.id,
        })
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'currency_id': self.currency_foreign.id,
            'invoice_date': '2026-05-01',
            'rate_mode': 'custom',
            'selected_rate_id': rate_record.id,
        })
        comp_rate = self.company.currency_id._get_rates(self.company, '2026-05-01').get(self.company.currency_id.id, 1.0)
        expected = 1.35 / comp_rate
        self.assertAlmostEqual(move.invoice_currency_rate, expected)

    def test_02_account_refresh_rate(self):
        """Test resetting rate_mode to default on refresh."""
        rate_record = self.env['res.currency.rate'].create({
            'name': '2026-05-01 10:00:00',
            'rate': 1.35,
            'currency_id': self.currency_foreign.id,
            'company_id': self.company.id,
        })
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'currency_id': self.currency_foreign.id,
            'invoice_date': '2026-05-01',
            'rate_mode': 'custom',
            'selected_rate_id': rate_record.id,
        })
        move.refresh_invoice_currency_rate()
        self.assertEqual(move.rate_mode, 'default')
        self.assertFalse(move.selected_rate_id)
