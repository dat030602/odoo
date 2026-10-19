from unittest.mock import MagicMock
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from ..models.migration_step import ALLOWED_ACTIONS, REQUIRED_INPUTS


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
                'field_description': 'Combo Char Field',
                'ttype': 'char',
                'help': 'Tooltip for combo char',
            },
            # 3. view create
            {
                'object_type': 'view',
                'action': 'create',
                'model_name': 'x_combo_model',
                'view_name': 'x_combo_model_form',
                'view_type': 'form',
                'arch': '<form><sheet><field name="x_combo_char"/></sheet></form>',
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
                'action_name': 'Combo Action Create',
                'xml_id': 'meta_migrator.action_combo_create',
                'state': 'code',
                'code': 'record.write({"x_combo_char": "done"})\n',
            },
            # 6. server_action update
            {
                'object_type': 'server_action',
                'action': 'update',
                'model_name': 'x_combo_model',
                'action_name': 'Combo Action Update',
                'xml_id': 'meta_migrator.action_combo_update',
                'state': 'code',
                'code': 'record.write({"x_combo_char": "updated"})\n',
            },
            # 7. menu create
            {
                'object_type': 'menu',
                'action': 'create',
                'model_name': 'x_combo_model',
                'menu_name': 'Combo Menu',
                'parent_xml_id': 'base.menu_custom',
            },
            # 8. access_right create
            {
                'object_type': 'access_right',
                'action': 'create',
                'model_name': 'x_combo_model',
                'access_name': 'access_x_combo_model_user',
                'group_xml_id': 'base.group_user',
                'perm_read': True,
                'perm_write': True,
            },
            # 9. record_rule create
            {
                'object_type': 'record_rule',
                'action': 'create',
                'model_name': 'x_combo_model',
                'rule_name': 'Combo Rule Multi Company',
                'domain_force': "['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]",
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

        # Missing view_type for view create
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'view',
                'action': 'create',
                'model_name': 'x_combo_model',
            })

        # Missing xml_id for view update
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'view',
                'action': 'update',
            })

        # Malformed xml_id without dot
        with self.assertRaises(ValidationError):
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'view',
                'action': 'update',
                'xml_id': 'nodotxmlid',
            })

    def test_04_field_compute_depends_mutual_requirement(self):
        """Test: If depends is set, compute is required; if compute is set, depends is required."""
        # Case A: compute set, depends empty -> ValidationError
        with self.assertRaises(ValidationError) as cm:
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_combo_model',
                'field_name': 'x_comp_no_dep',
                'ttype': 'char',
                'compute': 'for rec in self: rec.x_comp_no_dep = "ok"',
                'depends': '',
            })
        self.assertIn("depends", str(cm.exception).lower())

        # Case B: depends set, compute empty -> ValidationError
        with self.assertRaises(ValidationError) as cm:
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_combo_model',
                'field_name': 'x_dep_no_comp',
                'ttype': 'char',
                'compute': False,
                'depends': 'x_source_field',
            })
        self.assertIn("compute", str(cm.exception).lower())

        # Case C: both compute and depends set -> Success
        step_ok = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'field',
            'action': 'create',
            'model_name': 'x_combo_model',
            'field_name': 'x_comp_with_dep',
            'ttype': 'char',
            'compute': 'for rec in self: rec.x_comp_with_dep = "ok"',
            'depends': 'x_source_field',
            'help': 'Computed field with dependency',
        })
        self.assertTrue(step_ok.exists())
        self.assertEqual(step_ok.help, 'Computed field with dependency')

    def test_05_field_related_mutual_exclusion(self):
        """Test: If related is set, depends and compute cannot be set."""
        # Case A: related with compute -> ValidationError
        with self.assertRaises(ValidationError) as cm:
            self.env['meta.migration.step'].create({
                'job_id': self.job.id,
                'object_type': 'field',
                'action': 'create',
                'model_name': 'x_combo_model',
                'field_name': 'x_rel_and_comp',
                'ttype': 'char',
                'related': 'partner_id.name',
                'compute': 'for rec in self: pass',
                'depends': 'partner_id',
            })
        self.assertIn("related", str(cm.exception).lower())

        # Case B: related alone -> Success
        step_rel = self.env['meta.migration.step'].create({
            'job_id': self.job.id,
            'object_type': 'field',
            'action': 'create',
            'model_name': 'x_combo_model',
            'field_name': 'x_rel_alone',
            'ttype': 'char',
            'related': 'partner_id.name',
            'help': 'Related field from partner',
        })
        self.assertTrue(step_rel.exists())
        self.assertFalse(step_rel.compute)
        self.assertFalse(step_rel.depends)

    def test_06_field_onchange_behavior(self):
        """Test onchange methods: setting related clears compute/depends, setting compute clears related."""
        step = self.env['meta.migration.step'].new({
            'object_type': 'field',
            'action': 'create',
            'compute': 'for rec in self: pass',
            'depends': 'partner_id',
        })
        # Trigger onchange related
        step.related = 'partner_id.name'
        step._onchange_related()
        self.assertFalse(step.compute)
        self.assertFalse(step.depends)

        # Trigger onchange compute/depends
        step.compute = 'for rec in self: pass'
        step.depends = 'partner_id'
        step._onchange_compute_depends()
        self.assertFalse(step.related)

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
        mock_ctx['target_rpc'].search_read.return_value = [{'id': 1}]

        step_create_view = {
            'action': 'create',
            'object_type': 'view',
            'model_name': 'res.partner',
            'view_type': 'form',
            'view_name': 'res.partner.form.test',
            'arch': '<form><sheet/></form>',
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
