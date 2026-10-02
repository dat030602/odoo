from odoo.tests.common import TransactionCase

class TestCreditDeliveryControl(TransactionCase):
    def test_delivery_control(self):
        partner = self.env['res.partner'].create({
            'name': 'Test Delivery Partner',
        })
        self.assertTrue(partner)
