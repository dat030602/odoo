import unittest
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.meta_migrator.models.rpc_helper import OdooRPCError


class FakeRPC:
    """Mock XML-RPC client simulating remote Odoo database with in-memory dicts."""

    def __init__(self, db_state=None, read_only=False):
        self.db = db_state or {}
        self.read_only = read_only
        self.calls = []
        self._next_id = 100

    def authenticate(self):
        return 1

    def execute(self, model, method, *args, **kwargs):
        self.calls.append((model, method, args, kwargs))
        if self.read_only and method in ('create', 'write', 'unlink'):
            raise OdooRPCError('Blocked in test mode: %s.%s' % (model, method))
        if hasattr(self, method):
            return getattr(self, method)(model, *args, **kwargs)
        return True

    def search_read(self, model, domain, fields=None, limit=0, order=None, _retry=0):
        records = self.db.get(model, [])
        matched = []
        for r in records:
            if self._eval_domain(r, domain):
                if fields:
                    subset = {k: r.get(k) for k in fields}
                    if 'id' in r:
                        subset['id'] = r['id']
                    matched.append(subset)
                else:
                    matched.append(dict(r))
        if limit:
            matched = matched[:limit]
        return matched

    def search(self, model, domain, limit=0, _retry=0):
        res = self.search_read(model, domain, ['id'], limit=limit)
        return [r['id'] for r in res]

    def read(self, model, ids, fields=None, _retry=0):
        records = self.db.get(model, [])
        out = []
        for r in records:
            if r['id'] in ids:
                subset = {k: r.get(k) for k in fields} if fields else dict(r)
                subset['id'] = r['id']
                out.append(subset)
        return out

    def create(self, model, values):
        if self.read_only:
            raise OdooRPCError('Blocked in test mode: %s.create' % model)
        self._next_id += 1
        rec = dict(values, id=self._next_id)
        self.db.setdefault(model, []).append(rec)
        return self._next_id

    def write(self, model, ids, values):
        if self.read_only:
            raise OdooRPCError('Blocked in test mode: %s.write' % model)
        for r in self.db.get(model, []):
            if r['id'] in ids:
                r.update(values)
        return True

    def _eval_leaf(self, record, leaf):
        field, op, val = leaf
        if '.' in field:
            parts = field.split('.')
            cur = record
            for p in parts:
                if isinstance(cur, dict):
                    cur = cur.get(p)
                elif isinstance(cur, (list, tuple)) and len(cur) > 1 and p == 'model':
                    cur = cur[1]
                elif isinstance(cur, (list, tuple)) and len(cur) > 0 and p == 'id':
                    cur = cur[0]
                else:
                    cur = None
                    break
            rec_val = cur
        else:
            rec_val = record.get(field)
        if isinstance(rec_val, (list, tuple)) and rec_val and not isinstance(val, (list, tuple)):
            rec_val = rec_val[0]
        if op == '=':
            return rec_val == val
        elif op == '!=':
            return rec_val != val
        elif op == 'in':
            return rec_val in val if isinstance(val, (list, tuple, set)) else False
        return True

    def _eval_domain(self, record, domain):
        if not domain:
            return True
        stack = []
        for item in reversed(domain):
            if item == '&':
                a = stack.pop() if stack else True
                b = stack.pop() if stack else True
                stack.append(a and b)
            elif item == '|':
                a = stack.pop() if stack else True
                b = stack.pop() if stack else True
                stack.append(a or b)
            elif item == '!':
                a = stack.pop() if stack else True
                stack.append(not a)
            elif isinstance(item, (list, tuple)) and len(item) == 3:
                stack.append(self._eval_leaf(record, item))
            else:
                stack.append(True)
        return all(stack)


@tagged('post_install', '-at_install')
class TestPlanner(TransactionCase):

    def setUp(self):
        super().setUp()
        self.conn_src = self.env['meta.migration.connection'].create({
            'name': 'Source Link',
            'url': 'http://source.odoo',
            'db': 'source_db',
            'username': 'admin',
            'password': 'pwd',
        })
        self.conn_tgt = self.env['meta.migration.connection'].create({
            'name': 'Target Link',
            'url': 'http://target.odoo',
            'db': 'target_db',
            'username': 'admin',
            'password': 'pwd',
        })
        self.job = self.env['meta.migration.job'].create({
            'name': 'Test Job',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'on_conflict': 'overwrite',
        })

    def test_circular_dependency_planning(self):
        """Test parent (o2m) <-> child (m2o) circular relations in field block."""
        source_db = {
            'ir.model': [
                {'id': 1, 'model': 'x_parent', 'name': 'Parent Model', 'state': 'manual', 'transient': False},
                {'id': 2, 'model': 'x_child', 'name': 'Child Model', 'state': 'manual', 'transient': False},
            ],
            'ir.model.fields': [
                {
                    'id': 10, 'model': 'x_parent', 'name': 'x_child_ids', 'ttype': 'one2many',
                    'relation': 'x_child', 'relation_field': 'x_parent_id', 'state': 'manual',
                    'store': True, 'field_description': 'Children',
                },
                {
                    'id': 11, 'model': 'x_child', 'name': 'x_parent_id', 'ttype': 'many2one',
                    'relation': 'x_parent', 'state': 'manual', 'store': True,
                    'field_description': 'Parent',
                },
            ],
        }
        target_db = {
            'ir.model': [],
            'ir.model.fields': [],
        }

        # Step 1: create model x_parent
        # Step 2: create model x_child
        # Step 3: create field x_parent
        # Step 4: create field x_child
        self.env['meta.migration.step'].create([
            {'job_id': self.job.id, 'sequence': 10, 'action': 'create', 'object_type': 'model', 'model_name': 'x_parent'},
            {'job_id': self.job.id, 'sequence': 20, 'action': 'create', 'object_type': 'model', 'model_name': 'x_child'},
            {'job_id': self.job.id, 'sequence': 30, 'action': 'create', 'object_type': 'field', 'model_name': 'x_parent'},
            {'job_id': self.job.id, 'sequence': 40, 'action': 'create', 'object_type': 'field', 'model_name': 'x_child'},
        ])

        from unittest.mock import patch

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt = FakeRPC(target_db, read_only=True)

        run = self.job._create_run('test')

        def mock_get_rpc(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt

        # Execute dry-run test under mock
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run._execute()

        # Verify no create or write calls were made to target
        tgt_mutations = [c for c in fake_tgt.calls if c[1] in ('create', 'write', 'unlink')]
        self.assertEqual(len(tgt_mutations), 0, "Test mode must not perform remote writes!")

        # Verify all changes are planned successfully
        self.assertTrue(len(run.change_ids) >= 4)
        errors = run.change_ids.filtered(lambda c: c.change_type == 'error')
        self.assertEqual(len(errors), 0, f"Unexpected errors in circular test: {errors.mapped('message')}")

    def test_missing_relation_field_error(self):
        """Test that missing relation_field in one2many produces an error change with actionable hint."""
        from unittest.mock import patch

        source_db = {
            'ir.model': [
                {'id': 1, 'model': 'x_parent', 'name': 'Parent Model', 'state': 'manual', 'transient': False},
                {'id': 2, 'model': 'x_child', 'name': 'Child Model', 'state': 'manual', 'transient': False},
            ],
            'ir.model.fields': [
                {
                    'id': 10, 'model': 'x_parent', 'name': 'x_child_ids', 'ttype': 'one2many',
                    'relation': 'x_child', 'relation_field': 'x_parent_id', 'state': 'manual',
                    'store': True, 'field_description': 'Children',
                },
                # Notice: x_child has no x_parent_id
            ],
        }
        target_db = {'ir.model': [], 'ir.model.fields': []}

        self.env['meta.migration.step'].create([
            {'job_id': self.job.id, 'sequence': 10, 'action': 'create', 'object_type': 'model', 'model_name': 'x_parent'},
            {'job_id': self.job.id, 'sequence': 20, 'action': 'create', 'object_type': 'model', 'model_name': 'x_child'},
            {'job_id': self.job.id, 'sequence': 30, 'action': 'create', 'object_type': 'field', 'model_name': 'x_parent'},
        ])

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt = FakeRPC(target_db, read_only=True)

        def mock_get_rpc(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt

        run = self.job._create_run('test')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run._execute()

        errors = run.change_ids.filtered(lambda c: c.change_type == 'error')
        self.assertTrue(len(errors) > 0)
        self.assertIn('x_parent_id', errors[0].message)

    def test_planner_with_direct_step_setup(self):
        """Test planning when steps directly configure model, field, view, action definitions."""
        self.env['meta.migration.step'].create([
            {
                'job_id': self.job.id,
                'sequence': 10,
                'action': 'create',
                'object_type': 'model',
                'model_name': 'x_custom_invoice',
                'model_description': 'Custom Invoice',
                'create_menu': False,
            },
            {
                'job_id': self.job.id,
                'sequence': 20,
                'action': 'create',
                'object_type': 'field',
                'model_name': 'x_custom_invoice',
                'field_name': 'x_custom_note',
            },
            {
                'job_id': self.job.id,
                'sequence': 30,
                'action': 'create',
                'object_type': 'view',
                'model_name': 'x_custom_invoice',
            },
            {
                'job_id': self.job.id,
                'sequence': 40,
                'action': 'create',
                'object_type': 'server_action',
                'xml_id': 'custom.action_notify',
                'model_name': 'x_custom_invoice',
            },
            {
                'job_id': self.job.id,
                'sequence': 50,
                'action': 'create',
                'object_type': 'access_right',
                'model_name': 'x_custom_invoice',
            },
        ])

        source_db = {
            'ir.model': [
                {'id': 1, 'model': 'x_custom_invoice', 'name': 'Custom Invoice', 'state': 'manual'},
            ],
            'ir.model.fields': [
                {'id': 201, 'model': 'x_custom_invoice', 'name': 'x_custom_note', 'field_description': 'Custom Note', 'ttype': 'char', 'required': True, 'store': True, 'state': 'manual'},
            ],
            'ir.ui.view': [
                {'id': 301, 'name': 'custom_invoice_form', 'model': 'x_custom_invoice', 'type': 'form', 'arch': '<form><sheet><field name="x_custom_note"/></sheet></form>', 'priority': 16, 'active': True},
            ],
            'ir.actions.server': [
                {'id': 401, 'name': 'Send Notification', 'model_id': (1, 'x_custom_invoice'), 'state': 'code', 'code': 'record.write({"x_custom_note": "Notified"})', 'binding_model_id': False, 'binding_type': 'action'},
            ],
            'ir.model.access': [
                {'id': 501, 'name': 'access_custom_invoice_user', 'model_id': (1, 'x_custom_invoice'), 'group_id': False, 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': False},
            ],
            'ir.model.data': [
                {'id': 41, 'module': 'custom', 'name': 'action_notify', 'model': 'ir.actions.server', 'res_id': 401},
            ],
        }
        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt = FakeRPC({}, read_only=True)

        def mock_get_rpc(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt

        run = self.job._create_run('test')
        from unittest.mock import patch
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run._execute()

        changes = run.change_ids
        self.assertEqual(len(changes), 5)
        for c in changes:
            self.assertEqual(c.change_type, 'create', f"Change {c.name} expected create, got {c.change_type} ({c.message})")

    def test_view_migration_only_model_and_xml_id(self):
        """Test migrating views:
        1. Only model_name -> migrates all views on source for that model.
        2. With xml_id -> migrates only that 1 view.
        """
        from unittest.mock import patch

        source_db = {
            'ir.model': [{'id': 1, 'model': 'x_parent', 'name': 'Parent', 'state': 'manual'}],
            'ir.ui.view': [
                {'id': 101, 'name': 'parent.list', 'model': 'x_parent', 'type': 'list', 'arch': '<list><field name="name"/></list>', 'priority': 10, 'active': True},
                {'id': 102, 'name': 'parent.form', 'model': 'x_parent', 'type': 'form', 'arch': '<form><field name="name"/></form>', 'priority': 20, 'active': True},
            ],
            'ir.model.data': [
                {'id': 1, 'module': 'test_mod', 'name': 'view_parent_list', 'model': 'ir.ui.view', 'res_id': 101},
                {'id': 2, 'module': 'test_mod', 'name': 'view_parent_form', 'model': 'ir.ui.view', 'res_id': 102},
            ],
        }
        target_db = {
            'ir.model': [{'id': 1, 'model': 'x_parent', 'name': 'Parent', 'state': 'manual'}],
            'ir.ui.view': [],
            'ir.model.data': [],
        }

        # Step A: Only model_name
        job_all = self.env['meta.migration.job'].create({
            'name': 'Job All Views',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'on_conflict': 'overwrite',
        })
        self.env['meta.migration.step'].create({
            'job_id': job_all.id,
            'sequence': 10,
            'action': 'create',
            'object_type': 'view',
            'model_name': 'x_parent',
        })

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt = FakeRPC(target_db, read_only=True)

        def mock_get_rpc(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt

        run_all = job_all._create_run('test')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run_all._execute()

        # Both views planned
        view_changes = run_all.change_ids.filtered(lambda c: c.object_type == 'view')
        self.assertEqual(len(view_changes), 2, "Expected 2 views planned when only model_name is provided")
        self.assertTrue(all(c.change_type == 'create' for c in view_changes))

        # Test execute in run mode
        fake_tgt_write = FakeRPC(dict(target_db), read_only=False)
        def mock_get_rpc_write(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt_write

        run_apply = job_all._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_apply._execute()
        self.assertEqual(len(fake_tgt_write.db.get('ir.ui.view', [])), 2, "Both views should be created on target")

        # Step B: With xml_id -> only that 1 view
        job_one = self.env['meta.migration.job'].create({
            'name': 'Job One View',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
        })
        self.env['meta.migration.step'].create({
            'job_id': job_one.id,
            'sequence': 10,
            'action': 'create',
            'object_type': 'view',
            'model_name': 'x_parent',
            'xml_id': 'test_mod.view_parent_form',
        })
        run_one = job_one._create_run('test')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run_one._execute()

        self.assertEqual(len(run_one.change_ids), 1)
        self.assertIn('parent.form', run_one.change_ids[0].name)

    def test_server_action_migration_only_model_and_xml_id(self):
        """Test migrating server actions:
        1. Only model_name -> migrates all actions on source for that model.
        2. With xml_id -> migrates only that 1 action.
        """
        from unittest.mock import patch

        source_db = {
            'ir.model': [{'id': 1, 'model': 'x_parent', 'name': 'Parent', 'state': 'manual'}],
            'ir.actions.server': [
                {'id': 201, 'name': 'Action One', 'model_id': (1, 'x_parent'), 'state': 'code', 'code': 'pass', 'binding_model_id': False, 'binding_type': 'action'},
                {'id': 202, 'name': 'Action Two', 'model_id': (1, 'x_parent'), 'state': 'code', 'code': 'record.write({})', 'binding_model_id': False, 'binding_type': 'action'},
            ],
            'ir.model.data': [
                {'id': 11, 'module': 'test_mod', 'name': 'act_one', 'model': 'ir.actions.server', 'res_id': 201},
                {'id': 12, 'module': 'test_mod', 'name': 'act_two', 'model': 'ir.actions.server', 'res_id': 202},
            ],
        }
        target_db = {
            'ir.model': [{'id': 1, 'model': 'x_parent', 'name': 'Parent', 'state': 'manual'}],
            'ir.actions.server': [],
            'ir.model.data': [],
        }

        # Step A: Only model_name
        job_all = self.env['meta.migration.job'].create({
            'name': 'Job All SA',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'on_conflict': 'overwrite',
        })
        self.env['meta.migration.step'].create({
            'job_id': job_all.id,
            'sequence': 10,
            'action': 'create',
            'object_type': 'server_action',
            'model_name': 'x_parent',
        })

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt = FakeRPC(target_db, read_only=True)

        def mock_get_rpc(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt

        run_all = job_all._create_run('test')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run_all._execute()

        sa_changes = run_all.change_ids.filtered(lambda c: c.object_type == 'server_action')
        self.assertEqual(len(sa_changes), 2, "Expected 2 server actions planned when only model_name is provided")
        self.assertTrue(all(c.change_type == 'create' for c in sa_changes))

        # Test execute in run mode
        fake_tgt_write = FakeRPC(dict(target_db), read_only=False)
        def mock_get_rpc_write(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt_write

        run_apply = job_all._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_apply._execute()
        self.assertEqual(len(fake_tgt_write.db.get('ir.actions.server', [])), 2, "Both server actions should be created on target")

        # Step B: With xml_id -> only that 1 action
        job_one = self.env['meta.migration.job'].create({
            'name': 'Job One SA',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
        })
        self.env['meta.migration.step'].create({
            'job_id': job_one.id,
            'sequence': 10,
            'action': 'create',
            'object_type': 'server_action',
            'model_name': 'x_parent',
            'xml_id': 'test_mod.act_one',
        })
        run_one = job_one._create_run('test')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run_one._execute()

        self.assertEqual(len(run_one.change_ids), 1)
        self.assertEqual(run_one.change_ids[0].target_ref, 'test_mod.act_one')

    def test_model_migration_when_model_exists_checks_and_runs_fields(self):
        """Test: If model already exists on target, creating model step checks fields:
        - Missing field -> planned as create, created in run mode
        - Changed field -> planned as update, updated in run mode
        - Unchanged field -> planned as unchanged
        """
        from unittest.mock import patch

        source_db = {
            'ir.model': [{'id': 1, 'model': 'x_parent', 'name': 'Parent Model', 'state': 'manual', 'transient': False}],
            'ir.model.fields': [
                {'id': 10, 'model': 'x_parent', 'name': 'x_sync', 'ttype': 'char', 'state': 'manual', 'field_description': 'Synced', 'store': True, 'required': False},
                {'id': 11, 'model': 'x_parent', 'name': 'x_diff', 'ttype': 'char', 'state': 'manual', 'field_description': 'New Label', 'store': True, 'required': True},
                {'id': 12, 'model': 'x_parent', 'name': 'x_new', 'ttype': 'char', 'state': 'manual', 'field_description': 'Missing On Target', 'store': True, 'required': False},
            ],
        }
        # Model already exists on target with x_sync and older x_diff
        target_db = {
            'ir.model': [{'id': 1, 'model': 'x_parent', 'name': 'Parent Model', 'state': 'manual', 'transient': False}],
            'ir.model.fields': [
                {'id': 50, 'model_id': 1, 'model': 'x_parent', 'name': 'x_sync', 'ttype': 'char', 'state': 'manual', 'field_description': 'Synced', 'store': True, 'required': False},
                {'id': 51, 'model_id': 1, 'model': 'x_parent', 'name': 'x_diff', 'ttype': 'char', 'state': 'manual', 'field_description': 'Old Label', 'store': True, 'required': False},
            ],
        }

        job = self.env['meta.migration.job'].create({
            'name': 'Job Model Exists',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'on_conflict': 'overwrite',
        })
        self.env['meta.migration.step'].create({
            'job_id': job.id,
            'sequence': 10,
            'action': 'create',
            'object_type': 'model',
            'model_name': 'x_parent',
            'create_list_view': False,
            'create_form_view': False,
            'create_search_view': False,
            'create_menu': False,
            'copy_access_rights': False,
            'copy_record_rules': False,
        })

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt = FakeRPC(target_db, read_only=True)

        def mock_get_rpc(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt

        # 1. Test mode check
        run_test = job._create_run('test')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run_test._execute()

        changes = run_test.change_ids
        # 1 model change + 3 field changes = 4 changes
        self.assertEqual(len(changes), 4)

        model_ch = changes.filtered(lambda c: c.object_type == 'model')
        self.assertEqual(model_ch.change_type, 'unchanged')

        field_sync = changes.filtered(lambda c: c.target_ref == 'x_parent.x_sync')
        self.assertEqual(field_sync.change_type, 'unchanged')

        field_diff = changes.filtered(lambda c: c.target_ref == 'x_parent.x_diff')
        self.assertEqual(field_diff.change_type, 'update')

        field_new = changes.filtered(lambda c: c.target_ref == 'x_parent.x_new')
        self.assertEqual(field_new.change_type, 'create')

        # 2. Run mode execution
        fake_tgt_write = FakeRPC(dict(target_db), read_only=False)
        def mock_get_rpc_write(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt_write

        run_exec = job._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_exec._execute()

        tgt_f_names = [f['name'] for f in fake_tgt_write.db.get('ir.model.fields', [])]
        self.assertIn('x_new', tgt_f_names, "Missing field x_new must be created on target")
        diff_f = [f for f in fake_tgt_write.db.get('ir.model.fields', []) if f['name'] == 'x_diff'][0]
        self.assertEqual(diff_f.get('field_description'), 'New Label', "Changed field x_diff must be updated on target")
        self.assertTrue(diff_f.get('required'), "Changed field x_diff required attribute must be updated")

    def test_model_migration_with_auto_create_options(self):
        """Test model step with related options (menu, access rights, views) auto-executes."""
        from unittest.mock import patch

        job = self.env['meta.migration.job'].create({
            'name': 'Job Model Related Options',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'on_conflict': 'overwrite',
        })
        self.env['meta.migration.step'].create({
            'job_id': job.id,
            'sequence': 10,
            'action': 'create',
            'object_type': 'model',
            'model_name': 'x_auto_model',
            'create_menu': True,
            'copy_access_rights': True,
            'copy_record_rules': True,
            'create_list_view': True,
            'create_form_view': True,
        })

        source_db = {
            'ir.model': [{'id': 1, 'model': 'x_auto_model', 'name': 'Auto Model', 'state': 'manual'}],
            'ir.model.fields': [
                {'id': 10, 'model': 'x_auto_model', 'name': 'x_name', 'field_description': 'Name', 'ttype': 'char', 'state': 'manual'},
            ],
            'ir.ui.view': [
                {'id': 20, 'model': 'x_auto_model', 'name': 'auto.list', 'type': 'list', 'arch': '<list><field name="x_name"/></list>', 'priority': 16, 'active': True},
                {'id': 21, 'model': 'x_auto_model', 'name': 'auto.form', 'type': 'form', 'arch': '<form><field name="x_name"/></form>', 'priority': 16, 'active': True},
            ],
            'ir.actions.act_window': [
                {'id': 30, 'name': 'Auto Model Action', 'res_model': 'x_auto_model', 'view_mode': 'list,form'},
            ],
            'ir.ui.menu': [
                {'id': 40, 'name': 'Auto Model Menu', 'action': 'ir.actions.act_window,30', 'sequence': 10, 'active': True},
            ],
            'ir.model.access': [
                {'id': 50, 'name': 'access_auto_model_user', 'model_id': (1, 'x_auto_model'), 'group_id': False, 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': True},
            ],
            'ir.rule': [
                {'id': 60, 'name': 'rule_auto_model', 'model_id': (1, 'x_auto_model'), 'domain_force': '[]', 'groups': [], 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': True, 'active': True},
            ],
            'ir.model.data': [],
        }
        target_db = {
            'ir.model': [],
            'ir.model.fields': [],
            'ir.ui.view': [],
            'ir.actions.act_window': [],
            'ir.ui.menu': [],
            'ir.model.access': [],
            'ir.rule': [],
            'ir.model.data': [],
        }

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt = FakeRPC(target_db, read_only=True)
        def mock_get_rpc(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt

        run_test = job._create_run('test')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run_test._execute()

        changes = run_test.change_ids
        object_types = {c.object_type for c in changes}
        self.assertIn('model', object_types)
        self.assertIn('field', object_types)
        self.assertIn('view', object_types)
        self.assertIn('menu', object_types)
        self.assertIn('access_right', object_types)
        self.assertIn('record_rule', object_types)

        # Run mode execution
        fake_tgt_write = FakeRPC(dict(target_db), read_only=False)
        def mock_get_rpc_write(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt_write

        run_exec = job._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_exec._execute()

        self.assertTrue(len(fake_tgt_write.db['ir.model']) > 0, "Model must be created")
        self.assertTrue(len(fake_tgt_write.db['ir.model.access']) > 0, "Access right must be created")
        self.assertTrue(len(fake_tgt_write.db['ir.actions.act_window']) > 0, "Window action must be created")
        self.assertTrue(len(fake_tgt_write.db['ir.ui.menu']) > 0, "Menu must be created")

    def test_xml_id_generation_and_migrated_lines(self):
        """Test that all created items get target XML IDs and are recorded in migrated_line_ids."""
        from unittest.mock import patch

        job = self.env['meta.migration.job'].create({
            'name': 'Job XML ID Test',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'target_module_name': 'test_migrator',
        })
        self.env['meta.migration.step'].create({
            'job_id': job.id,
            'object_type': 'model',
            'action': 'create',
            'model_name': 'x_xmlid_model',
            'model_description': 'XMLID Model',
            'create_form_view': True,
            'create_list_view': True,
            'copy_access_rights': True,
            'copy_record_rules': True,
            'create_menu': True,
        })

        source_db = {
            'ir.model': [{'id': 1, 'model': 'x_xmlid_model', 'name': 'XMLID Model', 'state': 'manual'}],
            'ir.model.fields': [
                {'id': 10, 'model': 'x_xmlid_model', 'name': 'x_test_field', 'field_description': 'Test Field', 'ttype': 'char', 'state': 'manual'},
            ],
            'ir.ui.view': [
                {'id': 20, 'model': 'x_xmlid_model', 'name': 'xmlid.list', 'type': 'list', 'arch': '<list><field name="x_test_field"/></list>', 'priority': 16, 'active': True},
            ],
            'ir.actions.act_window': [
                {'id': 30, 'name': 'XMLID Action', 'res_model': 'x_xmlid_model', 'view_mode': 'list,form'},
            ],
            'ir.ui.menu': [
                {'id': 40, 'name': 'XMLID Menu', 'action': 'ir.actions.act_window,30', 'sequence': 10, 'active': True},
            ],
            'ir.model.access': [
                {'id': 50, 'name': 'access_xmlid_model', 'model_id': (1, 'x_xmlid_model'), 'group_id': False, 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': True},
            ],
            'ir.rule': [
                {'id': 60, 'name': 'rule_xmlid_model', 'model_id': (1, 'x_xmlid_model'), 'domain_force': '[]', 'groups': [], 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': True, 'active': True},
            ],
            'ir.model.data': [],
        }
        target_db = {
            'ir.model': [],
            'ir.model.fields': [],
            'ir.ui.view': [],
            'ir.actions.act_window': [],
            'ir.ui.menu': [],
            'ir.model.access': [],
            'ir.rule': [],
            'ir.model.data': [],
        }

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt_write = FakeRPC(target_db, read_only=False)
        def mock_get_rpc_write(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt_write

        run_exec = job._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_exec._execute()

        # Check ir.model.data on target
        tgt_data = fake_tgt_write.db['ir.model.data']
        self.assertTrue(len(tgt_data) > 0, "ir.model.data entries must be created on target")
        for d in tgt_data:
            self.assertEqual(d['module'], 'test_migrator', "Module in XML ID must match job target_module_name")

        # Check job.migrated_line_ids
        lines = job.migrated_line_ids
        self.assertTrue(len(lines) > 0, "Job must have migrated lines recorded")
        line_types = {l.object_type for l in lines}
        self.assertIn('model', line_types)
        self.assertIn('field', line_types)
        self.assertIn('view', line_types)
        self.assertIn('menu', line_types)
        self.assertIn('access_right', line_types)
        self.assertIn('record_rule', line_types)

        for l in lines:
            self.assertTrue(l.xml_id.startswith('test_migrator.'), f"XML ID '{l.xml_id}' must start with 'test_migrator.'")
            self.assertEqual(l.state, 'applied')

    def test_action_id_replacement_in_view_arch(self):
        """Test replacing source server action ID with %(target_xml_id)d in view arch."""
        from unittest.mock import patch

        job = self.env['meta.migration.job'].create({
            'name': 'Job Action Replace Test',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'target_module_name': 'test_replace',
        })
        self.env['meta.migration.step'].create({
            'job_id': job.id,
            'object_type': 'view',
            'action': 'create',
            'model_name': 'x_btn_model',
        })

        source_db = {
            'ir.model': [{'id': 1, 'model': 'x_btn_model', 'name': 'Button Model', 'state': 'manual'}],
            'ir.actions.server': [
                {'id': 77, 'name': 'Action Do Magic', 'model_id': (1, 'x_btn_model'), 'state': 'code', 'code': 'pass'},
            ],
            'ir.ui.view': [
                {
                    'id': 101,
                    'model': 'x_btn_model',
                    'name': 'btn.form',
                    'type': 'form',
                    'arch': '<form><button name="%(77)d" type="action" string="Magic"/></form>',
                    'priority': 16,
                    'active': True,
                },
            ],
            'ir.model.data': [],
        }
        target_db = {
            'ir.model': [{'id': 1, 'model': 'x_btn_model', 'name': 'Button Model', 'state': 'manual'}],
            'ir.ui.view': [],
            'ir.model.data': [],
        }

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt_write = FakeRPC(target_db, read_only=False)
        def mock_get_rpc_write(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt_write

        run_exec = job._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_exec._execute()

        created_views = fake_tgt_write.db['ir.ui.view']
        self.assertTrue(len(created_views) > 0, "View must be created on target")
        view_arch = created_views[0]['arch']
        self.assertNotIn('%(77)d', view_arch, "Old source integer action ID 77 must be replaced")
        self.assertIn('%(test_replace.', view_arch, "Target XML ID must be in view arch")

    def test_anti_duplication_on_second_run(self):
        """Test that running the job a second time detects existing XML IDs and creates no duplicates."""
        from unittest.mock import patch

        job = self.env['meta.migration.job'].create({
            'name': 'Job Anti Duplication Test',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
            'target_module_name': 'anti_dup',
        })
        self.env['meta.migration.step'].create({
            'job_id': job.id,
            'object_type': 'server_action',
            'action': 'create',
            'model_name': 'x_dup_model',
        })

        source_db = {
            'ir.model': [{'id': 1, 'model': 'x_dup_model', 'name': 'Dup Model', 'state': 'manual'}],
            'ir.actions.server': [
                {'id': 88, 'name': 'Process Batch', 'model_id': (1, 'x_dup_model'), 'state': 'code', 'code': 'records.do()'},
            ],
            'ir.model.data': [],
        }
        target_db = {
            'ir.model': [{'id': 1, 'model': 'x_dup_model', 'name': 'Dup Model', 'state': 'manual'}],
            'ir.actions.server': [],
            'ir.model.data': [],
        }

        fake_src = FakeRPC(source_db, read_only=True)
        fake_tgt_write = FakeRPC(target_db, read_only=False)
        def mock_get_rpc_write(conn_self, read_only=False):
            if conn_self.id == self.conn_src.id:
                return fake_src
            return fake_tgt_write

        # 1st run
        run_1 = job._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_1._execute()

        actions_after_1 = len(fake_tgt_write.db['ir.actions.server'])
        data_after_1 = len(fake_tgt_write.db['ir.model.data'])
        self.assertEqual(actions_after_1, 1)
        self.assertEqual(data_after_1, 1)

        # 2nd run
        run_2 = job._create_run('run')
        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc_write):
            run_2._execute()

        actions_after_2 = len(fake_tgt_write.db['ir.actions.server'])
        data_after_2 = len(fake_tgt_write.db['ir.model.data'])
        self.assertEqual(actions_after_2, 1, "Second run must not create duplicate actions")
        self.assertEqual(data_after_2, 1, "Second run must not create duplicate ir.model.data entries")

    def test_virtual_field_structural_validation(self):
        """Test that invalid virtual fields are flagged as error changes during planning."""
        from unittest.mock import patch

        job = self.env['meta.migration.job'].create({
            'name': 'Job Virtual Field Validation',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
        })

        run = self.env['meta.migration.run'].create({
            'job_id': job.id,
            'mode': 'test',
            'source_connection_id': job.source_connection_id.id,
            'target_connection_id': job.target_connection_id.id,
            'on_conflict': 'skip',
            'state': 'queued',
            'total_steps': 1,
            'step_data': '[{"sequence": 10, "object_type": "field", "action": "create", "model_name": "x_test_model", "field_name": "x_bad_sel", "ttype": "selection"}]',
        })

        fake_src = FakeRPC({}, read_only=True)
        fake_tgt = FakeRPC({'ir.model': [{'id': 1, 'model': 'x_test_model', 'name': 'Test Model', 'state': 'manual'}]}, read_only=True)

        def mock_get_rpc(conn_self, read_only=False):
            return fake_src if conn_self.id == self.conn_src.id else fake_tgt

        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run._execute()

        err_changes = run.change_ids.filtered(lambda c: c.change_type == 'error')
        self.assertTrue(len(err_changes) > 0, "Must create an error change for selection missing options")
        self.assertIn("selection' options list is required", err_changes[0].message)

    def test_one2many_before_many2one_order_error(self):
        """Test that one2many running before many2one step produces an order error change."""
        from unittest.mock import patch

        job = self.env['meta.migration.job'].create({
            'name': 'Job O2M Order Error',
            'source_connection_id': self.conn_src.id,
            'target_connection_id': self.conn_tgt.id,
        })

        # Step 1: one2many (seq 10)
        # Step 2: many2one (seq 20)
        step_data = [
            {'sequence': 10, 'object_type': 'field', 'action': 'create', 'model_name': 'x_order', 'field_name': 'x_line_ids', 'ttype': 'one2many', 'relation': 'x_order_line', 'relation_field': 'x_order_id'},
            {'sequence': 20, 'object_type': 'field', 'action': 'create', 'model_name': 'x_order_line', 'field_name': 'x_order_id', 'ttype': 'many2one', 'relation': 'x_order'},
        ]

        import json
        run = self.env['meta.migration.run'].create({
            'job_id': job.id,
            'mode': 'test',
            'source_connection_id': job.source_connection_id.id,
            'target_connection_id': job.target_connection_id.id,
            'on_conflict': 'skip',
            'state': 'queued',
            'total_steps': 2,
            'step_data': json.dumps(step_data),
        })

        target_db = {
            'ir.model': [
                {'id': 1, 'model': 'x_order', 'name': 'Order', 'state': 'manual'},
                {'id': 2, 'model': 'x_order_line', 'name': 'Order Line', 'state': 'manual'},
            ],
            'ir.model.fields': [],
        }
        fake_src = FakeRPC({}, read_only=True)
        fake_tgt = FakeRPC(target_db, read_only=True)

        def mock_get_rpc(conn_self, read_only=False):
            return fake_src if conn_self.id == self.conn_src.id else fake_tgt

        with patch.object(type(self.conn_src), '_get_rpc', mock_get_rpc):
            run._execute()

        err_changes = run.change_ids.filtered(lambda c: c.change_type == 'error')
        self.assertTrue(len(err_changes) > 0, "Must create an error change for o2m running before m2o")
        self.assertIn("requires 'x_order_line.x_order_id' to be created first", err_changes[0].message)
        self.assertIn("Move the many2one step to a lower sequence number", err_changes[0].message)

