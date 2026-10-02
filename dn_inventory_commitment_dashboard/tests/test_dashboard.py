from odoo.tests.common import TransactionCase

class TestCommitmentDashboard(TransactionCase):
    def test_dashboard_model_exists(self):
        # We just verify the model is accessible since it's an auto=False SQL view
        env_model = self.env['inventory.commitment.report']
        self.assertTrue(env_model is not None)
