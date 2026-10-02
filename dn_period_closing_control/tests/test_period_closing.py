from odoo.tests.common import TransactionCase
from datetime import date

class TestPeriodClosingControl(TransactionCase):
    def test_lock_creation(self):
        lock = self.env['period.lock'].create({
            'company_id': self.env.company.id,
            'line_ids': [(0, 0, {
                'scope': 'sale',
                'lock_date': date.today()
            })]
        })
        self.assertEqual(len(lock.line_ids), 1)
