import unittest
from odoo.tests.common import TransactionCase
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

    def _eval_domain(self, record, domain):
        for leaf in domain:
            if not isinstance(leaf, (list, tuple)) or len(leaf) != 3:
                continue
            field, op, val = leaf
            rec_val = record.get(field)
            if op == '=':
                if rec_val != val:
                    return False
            elif op == '!=':
                if rec_val == val:
                    return False
            elif op == 'in':
                if rec_val not in val:
                    return False
        return True


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
            },
            {
                'job_id': self.job.id,
                'sequence': 20,
                'action': 'create',
                'object_type': 'field',
                'model_name': 'x_custom_invoice',
                'field_name': 'x_custom_note',
                'field_description': 'Custom Note',
                'ttype': 'char',
                'required': True,
                'store': True,
            },
            {
                'job_id': self.job.id,
                'sequence': 30,
                'action': 'create',
                'object_type': 'view',
                'model_name': 'x_custom_invoice',
                'view_name': 'custom_invoice_form',
                'view_type': 'form',
                'arch': '<form><sheet><field name="x_custom_note"/></sheet></form>',
            },
            {
                'job_id': self.job.id,
                'sequence': 40,
                'action': 'create',
                'object_type': 'server_action',
                'xml_id': 'custom.action_notify',
                'action_name': 'Send Notification',
                'model_name': 'x_custom_invoice',
                'code': 'record.write({"x_custom_note": "Notified"})',
            },
            {
                'job_id': self.job.id,
                'sequence': 50,
                'action': 'create',
                'object_type': 'access_right',
                'model_name': 'x_custom_invoice',
                'access_name': 'access_custom_invoice_user',
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': False,
            },
        ])

        fake_src = FakeRPC({}, read_only=True)
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

