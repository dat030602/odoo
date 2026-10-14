import json
from datetime import datetime, timedelta

from odoo.tests.common import HttpCase, tagged
from ..core.lexer_rewriter import rewrite_quoted_names, restore_names


@tagged('post_install', '-at_install')
class TestGraphQLGateway(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Seed test service user with sales / contact access
        cls.test_service_user = cls.env['res.users'].create({
            'name': 'GraphQL Service User',
            'login': 'graphql_service_user',
            'email': 'service_user@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('base.group_partner_manager').id,
            ])],
        })

        # Seed API key with scope 'graphql' (expires in 30 days)
        cls.api_key_token = cls.env['res.users.apikeys'].with_user(cls.test_service_user).sudo()._generate(
            'graphql', 'Integration Test Key', datetime.utcnow() + timedelta(days=30)
        )

        # Seed expired API key for testing
        cls.expired_key_token = cls.env['res.users.apikeys'].with_user(cls.test_service_user).sudo()._generate(
            'graphql', 'Expired Test Key', datetime.utcnow() - timedelta(days=1)
        )

    def _graphql_post(self, query, variables=None, token=None, content_type='application/json'):
        headers = {
            'Content-Type': content_type,
        }
        if token is not None:
            headers['Authorization'] = f'Bearer {token}'

        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        return self.url_open(
            '/graphql',
            data=json.dumps(payload).encode('utf-8') if content_type == 'application/json' else b'binary_data',
            headers=headers
        )

    def test_01_lexer_rewriter(self):
        """Test rewriting quoted model names outside parentheses and restoring data keys."""
        src = 'query { "sale.order"(first: 10, domain: "[(\'state\', \'=\', \'sale\')]") { edges { node { id } } } }'
        rewritten, mapping = rewrite_quoted_names(src)
        self.assertIn('sale__order', rewritten)
        self.assertNotIn('"sale.order"', rewritten)
        self.assertIn("[('state', '=', 'sale')]", rewritten)
        self.assertEqual(mapping.get('sale__order'), 'sale.order')

        # Test restore
        data = {'sale__order': {'edges': [{'node': {'id': 1}}]}}
        restored = restore_names(data, mapping)
        self.assertIn('sale.order', restored)

    def test_02_auth_missing_header(self):
        """Verify unauthenticated request without header returns 401 UNAUTHENTICATED."""
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=None)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    def test_03_auth_invalid_token(self):
        """Verify request with invalid Bearer token returns 401 UNAUTHENTICATED."""
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token='INVALID_FAKE_TOKEN_12345')
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    def test_04_auth_expired_key(self):
        """Verify request with expired API key returns 401 KEY_EXPIRED."""
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=self.expired_key_token)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'KEY_EXPIRED')

    def test_05_upload_forbidden(self):
        """Verify multipart/form-data upload attempt returns 415 UPLOAD_NOT_ALLOWED."""
        headers = {
            'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundary',
            'Authorization': f'Bearer {self.api_key_token}'
        }
        res = self.url_open('/graphql', data=b'fake file upload body', headers=headers)
        self.assertEqual(res.status_code, 415)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UPLOAD_NOT_ALLOWED')

    def test_06_query_quoted_syntax(self):
        """Verify querying with exact quoted model syntax 'res.partner' works."""
        q = '''
        query {
            "res.partner"(first: 3) {
                totalCount
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                }
                edges {
                    cursor
                    node {
                        id
                        name
                        email
                    }
                }
            }
        }
        '''
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('data', body)
        self.assertIn('res.partner', body['data'])
        self.assertGreaterEqual(body['data']['res.partner']['totalCount'], 1)
        edges = body['data']['res.partner']['edges']
        self.assertTrue(len(edges) > 0)
        self.assertTrue(edges[0]['node']['name'])

    def test_07_query_unquoted_syntax(self):
        """Verify standard unquoted syntax res__partner works identically."""
        q = '''
        query {
            res__partner(first: 2) {
                totalCount
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
        '''
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('data', body)
        self.assertIn('res__partner', body['data'])

    def test_08_mutation_crud_lifecycle(self):
        """Verify Create, Update, and Delete mutations work seamlessly."""
        # 1. Create
        create_q = '''
        mutation {
            "res.partner.create"(values: { name: "GraphQL Test Partner Org", email: "graphql_test@example.com" }) {
                node {
                    id
                    name
                    email
                }
                userErrors {
                    message
                    code
                }
            }
        }
        '''
        res = self._graphql_post(create_q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('data', body)
        self.assertIn('res.partner.create', body['data'])
        node = body['data']['res.partner.create']['node']
        self.assertEqual(node['name'], 'GraphQL Test Partner Org')
        partner_id = node['id']
        self.assertTrue(partner_id)

        # 2. Update
        update_q = f'''
        mutation {{
            "res.partner.update"(id: {partner_id}, values: {{ name: "GraphQL Updated Partner Org" }}) {{
                node {{
                    id
                    name
                }}
                userErrors {{
                    message
                }}
            }}
        }}
        '''
        res_up = self._graphql_post(update_q, token=self.api_key_token)
        self.assertEqual(res_up.status_code, 200)
        body_up = res_up.json()
        self.assertEqual(body_up['data']['res.partner.update']['node']['name'], 'GraphQL Updated Partner Org')

        # 3. Delete
        del_q = f'''
        mutation {{
            "res.partner.delete"(id: {partner_id}) {{
                success
                id
                userErrors {{
                    message
                }}
            }}
        }}
        '''
        res_del = self._graphql_post(del_q, token=self.api_key_token)
        self.assertEqual(res_del.status_code, 200)
        body_del = res_del.json()
        self.assertTrue(body_del['data']['res.partner.delete']['success'])

    def test_09_mutation_atomic_savepoint_rollback(self):
        """
        Verify atomic savepoint rollback:
        When multiple mutations are executed in a single request and one fails,
        the ENTIRE request is rolled back. No records are committed.
        """
        unique_name = f"Atomic_Rollback_Target_{datetime.utcnow().timestamp()}"
        q = f'''
        mutation {{
            step1: "res.partner.create"(values: {{ name: "{unique_name}" }}) {{
                node {{
                    id
                    name
                }}
                userErrors {{
                    message
                }}
            }}
            step2: "res.partner.update"(id: 999999999, values: {{ name: "Will Fail" }}) {{
                node {{
                    id
                }}
                userErrors {{
                    message
                    code
                }}
            }}
        }}
        '''
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body.get('extensions', {}).get('rolledBack'), "Expected extensions.rolledBack: True")

        # Verify step1's record does NOT exist in the database!
        count = self.env['res.partner'].search_count([('name', '=', unique_name)])
        self.assertEqual(count, 0, "Record was committed despite mutation failure! Savepoint rollback failed.")

    def test_10_deny_policy_global(self):
        """Verify global deny rules block prohibited models (ir.model, res.users.password) immediately."""
        # Querying unexposed or denied model
        q = '''
        query {
            "ir.model"(first: 1) {
                totalCount
            }
        }
        '''
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertIn(res.status_code, (400, 403))
        body = res.json()
        err_code = body['errors'][0]['extensions']['code']
        self.assertIn(err_code, ('FORBIDDEN_RESOURCE', 'GRAPHQL_VALIDATION_FAILED'))

    def test_11_rotate_api_key_mutation(self):
        """Verify rotateApiKey mutation generates new token and invalidates old token."""
        rotate_q = '''
        mutation {
            rotateApiKey(expiresInDays: 45) {
                newKey
                expirationDate
                userErrors {
                    message
                    code
                }
            }
        }
        '''
        res = self._graphql_post(rotate_q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        payload = body['data']['rotateApiKey']
        new_key = payload['newKey']
        self.assertTrue(new_key)
        self.assertTrue(payload['expirationDate'])
        self.assertEqual(len(payload['userErrors']), 0)

        # Verify old key no longer works
        old_res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=self.api_key_token)
        self.assertEqual(old_res.status_code, 401)

        # Verify new key works immediately!
        new_res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=new_key)
        self.assertEqual(new_res.status_code, 200)
        self.assertIn('data', new_res.json())

    def test_12_audit_log_persists(self):
        """Verify dn.graphql.log model operates correctly and records execution metrics."""
        log = self.env['dn.graphql.log'].create({
            'request_id': 'TEST_LOG_UUID_001',
            'api_key_name': 'test_key...',
            'user_id': self.test_service_user.id,
            'ip_address': '127.0.0.1',
            'operation_name': 'test_operation',
            'query_text': 'mutation { rotateApiKey { newKey } }',
            'status_code': 200,
            'duration_ms': 12.4,
            'node_count': 1,
            'rolled_back': False,
        })
        self.assertTrue(log.id)
        self.assertEqual(log.status_code, 200)
        self.assertEqual(log.request_id, 'TEST_LOG_UUID_001')

    def test_13_api_key_management_ui_lifecycle(self):
        """Verify dn.graphql.key model creation, key generation, revoke and regenerate lifecycle."""
        key_record = self.env['dn.graphql.key'].create({
            'name': 'Native Test Gateway Key',
            'user_id': self.test_service_user.id,
            'expiration_date': datetime.utcnow() + timedelta(days=90),
        })
        self.assertEqual(key_record.state, 'draft')
        self.assertFalse(key_record.raw_key)

        # 1. Generate Key
        key_record.action_generate_key()
        self.assertEqual(key_record.state, 'active')
        raw_token = key_record.raw_key
        self.assertTrue(raw_token)
        self.assertTrue(key_record.key_index)

        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=raw_token)
        self.assertEqual(res.status_code, 200)

        # 2. Revoke Key
        key_record.action_revoke_key()
        self.assertEqual(key_record.state, 'revoked')
        self.assertFalse(key_record.raw_key)

        res_rev = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=raw_token)
        self.assertEqual(res_rev.status_code, 401)

        # 3. Regenerate Key
        key_record.action_regenerate_key()
        self.assertEqual(key_record.state, 'active')
        new_token = key_record.raw_key
        self.assertTrue(new_token)
        self.assertNotEqual(new_token, raw_token)

        res_new = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=new_token)
        self.assertEqual(res_new.status_code, 200)

    def test_14_call_business_methods(self):
        """Verify calling business methods via '<model>.call' and 'callMethod'."""
        partner = self.env['res.partner'].search([], limit=1)

        # 1. Model-specific method call ("res.partner.call")
        q_call = f'''
        mutation CallMethod($args: String) {{
            "res.partner.call"(id: {partner.id}, method: "check_access_rights", args: $args) {{
                success
                result
                userErrors {{
                    message
                    code
                }}
            }}
        }}
        '''
        res = self._graphql_post(q_call, variables={'args': '["read"]'}, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('data', body)
        self.assertIn('res.partner.call', body['data'])
        self.assertTrue(body['data']['res.partner.call']['success'])

        # 2. Dynamic top-level callMethod
        q_generic = f'''
        mutation GenericCall($args: String) {{
            callMethod(model: "res.partner", id: {partner.id}, method: "check_access_rights", args: $args) {{
                success
                result
                userErrors {{
                    message
                }}
            }}
        }}
        '''
        res_gen = self._graphql_post(q_generic, variables={'args': '["read"]'}, token=self.api_key_token)
        self.assertEqual(res_gen.status_code, 200)
        body_gen = res_gen.json()
        self.assertTrue(body_gen['data']['callMethod']['success'])

        # 3. Private method rejection
        q_priv = f'''
        mutation {{
            "res.partner.call"(id: {partner.id}, method: "_compute_display_name") {{
                success
                userErrors {{
                    message
                }}
            }}
        }}
        '''
        res_priv = self._graphql_post(q_priv, token=self.api_key_token)
        body_priv = res_priv.json()
        self.assertTrue(bool(body_priv.get('errors')) or body_priv.get('data', {}).get('res.partner.call') is None)

        # 4. Non-existent method rejection
        q_nonexistent = f'''
        mutation {{
            "res.partner.call"(id: {partner.id}, method: "non_existent_method_xyz") {{
                success
                userErrors {{
                    message
                    code
                }}
            }}
        }}
        '''
        res_non = self._graphql_post(q_nonexistent, token=self.api_key_token)
        self.assertEqual(res_non.status_code, 200)
        body_non = res_non.json()
        self.assertFalse(body_non['data']['res.partner.call']['success'])
        self.assertEqual(body_non['data']['res.partner.call']['userErrors'][0]['code'], 'METHOD_NOT_FOUND')

    def test_15_request_response_body_and_key_logging(self):
        """Verify request and response body logging linked directly to dn.graphql.key and user."""
        test_user = self.env['res.users'].create({
            'name': 'GraphQL Audit Test User',
            'login': 'graphql_audit_user',
            'email': 'audit_user@example.com',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('base.group_partner_manager').id,
            ])],
        })

        # Create dn.graphql.key management record
        key_record = self.env['dn.graphql.key'].create({
            'name': 'Audit Key Integration Test',
            'user_id': test_user.id,
        })
        key_record.action_generate_key()

        self.assertEqual(key_record.state, 'active')
        self.assertTrue(key_record.raw_key)
        self.assertTrue(key_record.key_index)

        # Send GraphQL query using the generated key
        query = '{ "res.partner"(first: 1) { totalCount edges { node { id } } } }'
        res = self._graphql_post(query, token=key_record.raw_key)
        self.assertEqual(res.status_code, 200)
        res_data = res.json()
        self.assertIn('data', res_data)

        # Verify audit log in database
        log = self.env['dn.graphql.log'].search([
            '|',
            ('key_rec_id', '=', key_record.id),
            ('api_key_name', '=like', f"{key_record.key_index}%")
        ], limit=1)

        self.assertTrue(log, "Expected log record to be created in dn.graphql.log")
        self.assertEqual(log.user_id.id, test_user.id)
        self.assertEqual(log.status_code, 200)
        self.assertTrue(log.request_body, "Expected request_body to be saved")
        self.assertTrue(log.response_body, "Expected response_body to be saved")
        self.assertIn('res.partner', log.request_body)
        self.assertIn('totalCount', log.response_body)

        # Verify log is attached to the dn.graphql.key record
        self.assertIn(log, key_record.log_ids)
        self.assertGreaterEqual(key_record.log_count, 1)

