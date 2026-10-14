from odoo.tests.common import TransactionCase


class TestMrpCostPreValidation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Product with 0 standard price
        cls.raw_zero = cls.env['product.product'].create({
            'name': 'Test Zero Cost Material',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 0.0,
        })
        cls.finished_bad = cls.env['product.product'].create({
            'name': 'Test Finished Bad',
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'standard_price': 50.0,
        })

        # Work Center with 0 costs_hour
        cls.wc_zero = cls.env['mrp.workcenter'].create({
            'name': 'Zero Rate Workcenter',
            'costs_hour': 0.0,
        })

        # Faulty BOM: has component with 0 price & work center with 0 rate
        cls.bom_faulty = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.finished_bad.product_tmpl_id.id,
            'product_id': cls.finished_bad.id,
            'product_qty': 1.0,
            'product_uom_id': cls.uom_unit.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.raw_zero.id, 'product_qty': 1.0, 'product_uom_id': cls.uom_unit.id})
            ],
            'operation_ids': [
                (0, 0, {
                    'name': 'Test Op Zero WC',
                    'workcenter_id': cls.wc_zero.id,
                    'time_cycle_manual': 15.0,
                })
            ]
        })

    def test_pre_costing_audit(self):
        """Test running the pre-costing audit and detecting missing costs."""
        audit_model = self.env['mrp.cost.bom.exception']
        audit_model.action_run_audit()

        # Check that exceptions were created for our faulty BOM
        exceptions = audit_model.search([('bom_id', '=', self.bom_faulty.id)])
        self.assertTrue(len(exceptions) >= 2, 'Audit should catch both zero material cost and zero workcenter rate.')

        types = exceptions.mapped('exception_type')
        self.assertIn('zero_material_cost', types)
        self.assertIn('zero_workcenter_rate', types)
