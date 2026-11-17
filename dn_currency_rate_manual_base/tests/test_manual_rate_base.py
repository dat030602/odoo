from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestManualRateBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_usd = cls.env.ref('base.USD')
        cls.company = cls.env.company

        # Create a test model dynamically or test using res.currency.rate display_name
        cls.rate = cls.env['res.currency.rate'].create({
            'name': '2026-05-01 10:00:00',
            'rate': 1.25,
            'currency_id': cls.currency_usd.id,
            'company_id': cls.company.id,
        })

    def test_01_display_name_context(self):
        """Test display_name formatting with dynamic_rate_display context."""
        rate_with_ctx = self.rate.with_context(dynamic_rate_display=True)
        self.assertIn('1.25', rate_with_ctx.display_name)
        self.assertIn('USD', rate_with_ctx.display_name)
