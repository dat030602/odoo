from odoo.tests.common import TransactionCase

class TestCreditSaleControl(TransactionCase):
    def test_partner_credit_limit(self):
        partner = self.env['res.partner'].create({
            'name': 'Test Credit Partner',
            'credit_limit_amount': 1000.0,
            'credit_check_enabled': True
        })
        self.assertEqual(partner.credit_limit_amount, 1000.0)
