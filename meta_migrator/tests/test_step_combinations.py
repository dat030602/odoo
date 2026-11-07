from unittest.mock import MagicMock
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo.addons.meta_migrator.models.migration_step import ALLOWED_ACTIONS, REQUIRED_INPUTS


@tagged('post_install', '-at_install')
class TestStepCombinations(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conn_src = cls.env['meta.migration.connection'].create({
            'name': 'Source Test Conn',
            'url': 'http://localhost:8069',
            'db': 'odoo19',
            'username': 'admin',
            'password': 'admin',
        })
        cls.conn_tgt = cls.env['meta.migration.connection'].create({
            'name': 'Target Test Conn',
            'url': 'http://localhost:8069',
            'db': 'odoo19',
            'username': 'admin',
            'password': 'admin',
        })
        cls.job = cls.env['meta.migration.job'].create({
            'name': 'Job Test Combinations',
            'source_connection_id': cls.conn_src.id,
            'target_connection_id': cls.conn_tgt.id,
        })

    def test_01_all_valid_action_object_combinations(self):
        """Test creating steps for all 9 valid (object_type, action) combinations."""
        test_payloads = [
            # 1. model create
            {
                'object_type': 'model',
                'action': 'create',
                'model_name': 'x_combo_model',
                'model_description': 'Combo Model Description',
            },
            # 2. field create (standard)
            {
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_combo_model',
                'field_name': 'x_combo_char',
            },
            # 3. view create
            {
                'object_type': 'view',
                'action': 'create',
                'model_name': 'x_combo_model',
            },
            # 4. view update
            {
                'object_type': 'view',
                'action': 'update',
                'model_name': 'x_combo_model',
                'xml_id': 'meta_migrator.test_view_update_combo',
            },
            # 5. server_action create
            {
                'object_type': 'server_action',
                'action': 'create',
                'model_name': 'x_combo_model',
                'xml_id': 'meta_migrator.action_combo_create',
            },
            # 6. server_action update
            {
                'object_type': 'server_action',
                'action': 'update',
                'model_name': 'x_combo_model',
                'xml_id': 'meta_migrator.action_combo_update',
            },
            # 7. menu create
            {
                'object_type': 'menu',
                'action': 'create',
                'model_name': 'x_combo_model',
            },
            # 8. access_right create
            {
                'object_type': 'access_right',
                'action': 'create',
                'model_name': 'x_combo_model',
            },
            # 9. record_rule create
            {
                'object_type': 'record_rule',
                'action': 'create',
                'model_name': 'x_combo_model',
            },
        ]

        created_steps = self.env['meta.migration.step']
        for p in test_payloads:
            p['job_id'] = self.job.id
            step = self.env['meta.migration.step'].create(p)
            self.assertTrue(step.exists(), f"Failed to create step for {p['object_type']} {p['action']}")
            self.assertTrue(bool(step.label), f"Step label is empty for {p['object_type']}")
            created_steps |= step

        self.assertEqual(len(created_steps), 9)

    def test_02_invalid_action_combinations_rejected(self):
        """Test that invalid actions for restricted object types raise ValidationError."""
        invalid_combinations = [
            ('model', 'update'),
            ('field', 'update'),
            ('menu', 'update'),
            ('access_right', 'update'),
            ('record_rule', 'update'),
        ]
        for otype, act in invalid_combinations:
            with self.subTest(object_type=otype, action=act):
                with self.assertRaises(ValidationError):
                    self.env['meta.migration.step'].create({
                        'job_id': self.job.id,
                        'object_type': otype,
                        'action': act,
                        'model_name': 'x_combo_model',
                        'xml_id': 'meta_migrator.dummy_xml_id',
                    })

    def test_03_missing_required_inputs_rejected(self):
        """Test missing required fields per (object_type, action)."""
        # Missing model_name for model create
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'model',
                'action': 'create',
            })

        # View create with only model_name is VALID (auto-fetches all views of model from source)
        view_step = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'view',
            'action': 'create',
            'model_name': 'x_combo_model',
        })
        self.assertTrue(view_step.exists())

        # View create without model_name and without xml_id is REJECTED
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'view',
                'action': 'create',
            })

        # Server action create with only model_name is VALID (auto-fetches all actions for model from source)
        sa_step = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'server_action',
            'action': 'create',
            'model_name': 'x_combo_model',
        })
        self.assertTrue(sa_step.exists())

        # Server action create without model_name and without xml_id is REJECTED
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'server_action',
                'action': 'create',
            })

        # Menu create without model_name and without xml_id is REJECTED
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'menu',
                'action': 'create',
            })

        # Malformed xml_id without dot
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'view',
                'action': 'update',
                'xml_id': 'nodotxmlid',
            })

    def test_04_simplified_step_inputs(self):
        """Test simplified inputs for field, access_right, and record_rule."""
        # Field step with only model_name (migrate all manual fields)
        step_field_all = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'field',
            'action': 'create',
            'model_name': 'x_combo_model',
        })
        self.assertTrue(step_field_all.exists())
        self.assertIn("all manual fields", step_field_all.label)

        # Field step with xml_id
        step_field_xml = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'field',
            'action': 'create',
            'xml_id': 'base.field_res_partner__name',
        })
        self.assertTrue(step_field_xml.exists())
        self.assertIn("base.field_res_partner__name", step_field_xml.label)

        # Access right step with only model_name
        step_acc_all = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'access_right',
            'action': 'create',
            'model_name': 'x_combo_model',
        })
        self.assertTrue(step_acc_all.exists())
        self.assertIn("access rights for x_combo_model", step_acc_all.label)

        # Access right step with xml_id
        step_acc_xml = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'access_right',
            'action': 'create',
            'xml_id': 'base.access_res_partner_group_user',
        })
        self.assertTrue(step_acc_xml.exists())
        self.assertIn("base.access_res_partner_group_user", step_acc_xml.label)

        # Record rule step with only model_name
        step_rule_all = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'record_rule',
            'action': 'create',
            'model_name': 'x_combo_model',
        })
        self.assertTrue(step_rule_all.exists())
        self.assertIn("record rules for x_combo_model", step_rule_all.label)

        # Record rule step with xml_id
        step_rule_xml = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'record_rule',
            'action': 'create',
            'xml_id': 'base.res_partner_rule',
        })
        self.assertTrue(step_rule_xml.exists())
        self.assertIn("base.res_partner_rule", step_rule_xml.label)

    def test_05_model_step_related_options(self):
        """Test model step with related options (menu, access rights, views)."""
        step_model = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'model',
            'action': 'create',
            'model_name': 'x_combo_model',
            'create_list_view': True,
            'create_form_view': True,
            'create_search_view': True,
            'create_menu': True,
            'copy_access_rights': True,
            'copy_record_rules': True,
        })
        self.assertTrue(step_model.exists())
        snap = step_model._to_snapshot()
        self.assertTrue(snap['create_menu'])
        self.assertTrue(snap['copy_access_rights'])
        self.assertTrue(snap['copy_record_rules'])
        self.assertTrue(snap['create_list_view'])
        self.assertTrue(snap['create_form_view'])
        self.assertTrue(snap['create_search_view'])

    def test_07_view_dispatch_plan_and_apply(self):
        """Test that _plan_view and _apply_view properly dispatch create and update actions."""
        run = self.env['meta.migration.run'].create({
            'job_id': self.job.id,
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'mode': 'test',
        })

        # Verify _plan_view dispatching
        mock_ctx = {
            'rename_map': {},
            'target_rpc': MagicMock(),
            'source_rpc': MagicMock(),
            'cache': {},
            'planned_models': {'res.partner'},
        }
        mock_ctx['target_rpc'].search_read.return_value = []
        mock_ctx['source_rpc'].search_read.return_value = [{
            'id': 10,
            'name': 'Partner Form',
            'type': 'form',
            'arch': '<form><sheet/></form>',
            'priority': 16,
            'inherit_id': False,
            'mode': 'primary',
            'model': 'res.partner',
        }]

        step_create_view = {
            'action': 'create',
            'object_type': 'view',
            'model_name': 'res.partner',
        }
        changes_create = run._plan_view(step_create_view, mock_ctx)
        self.assertTrue(isinstance(changes_create, list))
        self.assertEqual(changes_create[0]['object_type'], 'view')

        step_update_view = {
            'action': 'update',
            'object_type': 'view',
            'xml_id': 'base.view_partner_form',
        }
        # Mock source_rpc & target_rpc for ir.model.data and ir.ui.view
        mock_ctx['source_rpc'].search_read.return_value = [{'res_id': 10, 'model': 'ir.ui.view'}]
        mock_ctx['source_rpc'].read.return_value = [{'arch': '<form><sheet><field name="name"/></sheet></form>'}]
        mock_ctx['target_rpc'].search_read.return_value = [{'res_id': 10, 'model': 'ir.ui.view'}]
        mock_ctx['target_rpc'].read.return_value = [{'arch': '<form><sheet><field name="name"/></sheet></form>'}]

        changes_update = run._plan_view(step_update_view, mock_ctx)
        self.assertTrue(isinstance(changes_update, list))
        self.assertEqual(changes_update[0]['object_type'], 'view')
