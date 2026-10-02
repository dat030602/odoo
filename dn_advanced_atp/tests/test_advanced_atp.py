from odoo.tests.common import TransactionCase

class TestAdvancedATP(TransactionCase):
    def test_allocation_rule(self):
        rule = self.env['allocation.rule'].create({
            'name': 'Test Rule',
            'active': True
        })
        self.assertEqual(rule.name, 'Test Rule')
