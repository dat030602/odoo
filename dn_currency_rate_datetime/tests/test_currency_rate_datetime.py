from datetime import datetime
from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestCurrencyRateDatetime(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency_eur = cls.env.ref('base.EUR')
        cls.currency_usd = cls.env.ref('base.USD')

        # Clean existing rates for test consistency
        cls.env['res.currency.rate'].search([
            ('currency_id', '=', cls.currency_usd.id),
            ('company_id', '=', cls.company.id),
        ]).unlink()

    def test_01_multiple_rates_same_day(self):
        """Test creating multiple rates for the same currency on the same day with different datetimes."""
        Rate = self.env['res.currency.rate']
        dt_morning = datetime(2026, 5, 1, 8, 0, 0)
        dt_noon = datetime(2026, 5, 1, 12, 0, 0)
        dt_evening = datetime(2026, 5, 1, 18, 0, 0)

        rate_1 = Rate.create({
            'name': dt_morning,
            'rate': 1.10,
            'currency_id': self.currency_usd.id,
            'company_id': self.company.id,
        })
        rate_2 = Rate.create({
            'name': dt_noon,
            'rate': 1.15,
            'currency_id': self.currency_usd.id,
            'company_id': self.company.id,
        })
        rate_3 = Rate.create({
            'name': dt_evening,
            'rate': 1.20,
            'currency_id': self.currency_usd.id,
            'company_id': self.company.id,
        })

        self.assertTrue(rate_1 and rate_2 and rate_3)

        # Check rate at 09:00: should be rate_1 (1.10)
        rates_0900 = self.currency_usd._get_rates(self.company, datetime(2026, 5, 1, 9, 0, 0))
        self.assertAlmostEqual(rates_0900.get(self.currency_usd.id), 1.10)

        # Check rate at 14:00: should be rate_2 (1.15)
        rates_1400 = self.currency_usd._get_rates(self.company, datetime(2026, 5, 1, 14, 0, 0))
        self.assertAlmostEqual(rates_1400.get(self.currency_usd.id), 1.15)

        # Check rate at 20:00: should be rate_3 (1.20)
        rates_2000 = self.currency_usd._get_rates(self.company, datetime(2026, 5, 1, 20, 0, 0))
        self.assertAlmostEqual(rates_2000.get(self.currency_usd.id), 1.20)

    def test_02_unique_per_second_constraint(self):
        """Test constraint allows only one rate per exact second."""
        Rate = self.env['res.currency.rate']
        dt = datetime(2026, 5, 2, 10, 30, 0)

        Rate.create({
            'name': dt,
            'rate': 1.12,
            'currency_id': self.currency_usd.id,
            'company_id': self.company.id,
        })

        with self.assertRaises(Exception), mute_logger('odoo.sql_db'):
            with self.cr.savepoint():
                Rate.create({
                    'name': dt,
                    'rate': 1.13,
                    'currency_id': self.currency_usd.id,
                    'company_id': self.company.id,
                })
