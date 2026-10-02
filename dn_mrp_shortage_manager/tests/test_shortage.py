from odoo.tests.common import TransactionCase

class TestMrpShortageManager(TransactionCase):
    def test_shortage_wizard(self):
        wizard = self.env['mrp.shortage.dashboard'].create({})
        self.assertTrue(wizard)
