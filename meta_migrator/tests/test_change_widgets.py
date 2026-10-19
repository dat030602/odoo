import json
from odoo.tests.common import TransactionCase
from .test_planner import FakeRPC


class TestChangeWidgets(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conn = cls.env['meta.migration.connection'].create({
            'name': 'Test Target',
            'url': 'http://localhost:8069',
            'db': 'test_db',
            'username': 'admin',
            'password': 'key',
        })
        cls.job = cls.env['meta.migration.job'].create({
            'name': 'Test Job',
            'source_connection_id': cls.conn.id,
            'target_connection_id': cls.conn.id,
        })
        cls.migration_run = cls.env['meta.migration.run'].create({
            'job_id': cls.job.id,
            'source_connection_id': cls.conn.id,
            'target_connection_id': cls.conn.id,
            'mode': 'test',
        })

    def test_widget_key_matrix(self):
        Change = self.env['meta.migration.change']

        matrix = [
            ('model', '', 'model_create'),
            ('model', '{"state": "manual"}', 'model_update'),
            ('field', '', 'field_create'),
            ('field', '{"ttype": "char"}', 'field_update'),
            ('view', '', 'view_create'),
            ('view', '<form/>', 'view_update'),
            ('server_action', '', 'server_action'),
            ('server_action', 'name: action\n--- code ---\npass', 'server_action'),
            ('menu', '', 'generic'),
            ('access_right', '{"perm_read": true}', 'generic'),
            ('record_rule', '{"domain_force": "[]"}', 'generic'),
            (False, '', False),
        ]

        for ot, old_raw, expected_key in matrix:
            c = Change.create({
                'run_id': self.migration_run.id,
                'name': f'test {ot}',
                'object_type': ot,
                'change_type': 'update' if old_raw else 'create',
                'old_raw': old_raw,
                'new_raw': 'some_val',
            })
            self.assertEqual(c.widget_key, expected_key, f"Failed for ot={ot}, old_raw='{old_raw}'")

    def test_children_json_partition(self):
        Change = self.env['meta.migration.change']

        m1 = Change.create({
            'run_id': self.migration_run.id,
            'object_type': 'model',
            'change_type': 'create',
            'name': 'model x_sale.report',
            'target_ref': 'x_sale.report',
            'new_raw': json.dumps({'model': 'x_sale.report', 'name': 'Sale Report'}),
        })

        m2 = Change.create({
            'run_id': self.migration_run.id,
            'object_type': 'model',
            'change_type': 'create',
            'name': 'model x_sale.report.line',
            'target_ref': 'x_sale.report.line',
            'new_raw': json.dumps({'model': 'x_sale.report.line', 'name': 'Sale Report Line'}),
        })

        f1 = Change.create({
            'run_id': self.migration_run.id,
            'object_type': 'field',
            'change_type': 'create',
            'name': 'field x_sale.report.x_amount',
            'target_ref': 'x_sale.report.x_amount',
            'new_raw': json.dumps({'name': 'x_amount', 'ttype': 'float'}),
        })

        f2 = Change.create({
            'run_id': self.migration_run.id,
            'object_type': 'field',
            'change_type': 'create',
            'name': 'field x_sale.report.line.x_qty',
            'target_ref': 'x_sale.report.line.x_qty',
            'new_raw': json.dumps({'name': 'x_qty', 'ttype': 'integer'}),
        })

        # Test children_json on m1
        children1 = json.loads(m1.children_json or '[]')
        self.assertEqual(len(children1), 1)
        self.assertEqual(children1[0]['name'], 'x_amount')
        self.assertEqual(children1[0]['vals']['ttype'], 'float')

        # Test children_json on m2
        children2 = json.loads(m2.children_json or '[]')
        self.assertEqual(len(children2), 1)
        self.assertEqual(children2[0]['name'], 'x_qty')
        self.assertEqual(children2[0]['vals']['ttype'], 'integer')

    def test_view_planner_extra_raw(self):
        src_db = {
            'ir.ui.view': [
                {
                    'id': 1,
                    'name': 'partner.list',
                    'model': 'res.partner',
                    'type': 'list',
                    'arch': '<list><field name="name"/></list>',
                    'priority': 20,
                    'active': True,
                    'inherit_id': [99, 'base.view_partner_tree'],
                },
            ],
            'ir.model.data': [
                {'id': 1, 'module': 'base', 'name': 'view_partner_form', 'model': 'ir.ui.view', 'res_id': 10},
            ],
        }
        src_db['ir.ui.view'].append({
            'id': 10,
            'arch': '<data><xpath expr="//sheet" position="inside"><field name="x_test"/></xpath></data>',
            'inherit_id': [50, 'base.view_partner_form_parent'],
            'model': 'res.partner',
        })

        tgt_db = {
            'ir.ui.view': [
                {
                    'id': 100,
                    'arch': '<data><sheet><field name="name"/></sheet></data>',
                    'inherit_id': [50, 'base.view_partner_form_parent'],
                    'model': 'res.partner',
                }
            ],
            'ir.model.data': [
                {'id': 100, 'module': 'base', 'name': 'view_partner_form', 'model': 'ir.ui.view', 'res_id': 100},
            ],
            'ir.model': [
                {'id': 1, 'model': 'res.partner', 'name': 'Contact', 'state': 'base', 'transient': False},
            ],
        }

        ctx = {
            'source_rpc': FakeRPC(src_db),
            'target_rpc': FakeRPC(tgt_db),
            'cache': {},
            'rename_map': {},
            'planned_models': set(),
            'planned_fields': set(),
        }

        # 1. Test _plan_view_create
        step_create = {
            'model_name': 'res.partner',
            'view_type': 'list',
        }
        res_create = self.migration_run._plan_view_create(step_create, ctx)
        self.assertEqual(len(res_create), 1)
        self.assertTrue(res_create[0].get('extra_raw'))
        extra_create = json.loads(res_create[0]['extra_raw'])
        self.assertEqual(extra_create['name'], 'partner.list')
        self.assertEqual(extra_create['type'], 'list')
        self.assertEqual(extra_create['priority'], 20)
        self.assertEqual(extra_create['inherit_name'], 'base.view_partner_tree')

        # 2. Test _plan_view_update
        step_update = {
            'xml_id': 'base.view_partner_form',
        }
        res_update = self.migration_run._plan_view_update(step_update, ctx)
        self.assertEqual(len(res_update), 1)
        self.assertTrue(res_update[0].get('extra_raw'))
        extra_update = json.loads(res_update[0]['extra_raw'])
        self.assertIn('added', extra_update)
        self.assertIn('present', extra_update)
        self.assertEqual(len(extra_update['added']), 1)
        self.assertIn('xpath', extra_update['added'][0])

    def test_change_read_empty_extra_raw(self):
        Change = self.env['meta.migration.change']
        c = Change.create({
            'run_id': self.migration_run.id,
            'name': 'old record test',
            'object_type': 'model',
            'change_type': 'create',
            'target_ref': 'x_demo',
            'old_raw': '',
            'new_raw': '{"model": "x_demo"}',
            'extra_raw': '',
        })
        # Verify read on computed fields succeeds without error
        data = c.read(['widget_key', 'children_json', 'extra_raw'])[0]
        self.assertEqual(data['widget_key'], 'model_create')
        self.assertEqual(data['extra_raw'], '')
        self.assertEqual(data['children_json'], '[]')
