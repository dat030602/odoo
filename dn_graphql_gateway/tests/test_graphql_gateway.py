import json
import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import odoo
from odoo.exceptions import AccessError
from odoo.tests.common import HttpCase, tagged
from ..core.lexer_rewriter import rewrite_quoted_names, restore_names

# Ensure local test requests bypass proxy in container sandbox
os.environ['no_proxy'] = 'localhost,127.0.0.1'
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'


@tagged('post_install', '-at_install')
class TestGraphQLGateway(HttpCase):
    """
    Comprehensive test suite for dn_graphql_gateway covering 100% features:
    - Authentication (Bearer token, scope, expiration, rotation)
    - Deactivated / Archived user access denial (Task 1 regression prevention)
    - Dynamic database determination & missing DB error (HTTP 400)
    - Schema generation & Relay GraphQL querying (pageInfo, totalCount, edges/node)
    - Exact quoted model syntax ("res.partner") and unquoted syntax (res__partner)
    - Atomic Savepoint Rollback on mutation failures
    - Multi-tier Deny / Blocklist (Global and per-API Key)
    - Field-level Deny policy (read and write restrictions)
    - Anti-Scraping protections (depth limit, max_limit clamping, max_nodes ceiling)
    - Rate Limiting (HTTP 429 RATE_LIMITED)
    - Upload prohibition (HTTP 415 UPLOAD_NOT_ALLOWED on multipart/form-data)
    - Audit Logging persistence & independence across rollbacks
    - Safe Domain AST Validation (syntax errors, forbidden field detection)
    - Business method calling & Private method guardrails
    - UI Management lifecycle for dn.graphql.key model
    - Scope strictness (rejection of scope IS NULL)
    - ACL isolation of dn.graphql.key against standard users (0,0,0,0)
    - Database unpersisted raw_key (store=False)
    - Atomic Upsert Postgres for Rate Limiter and Fail-closed error handling
    - Whitelist guard for callMethod
    - Recursive comodel relation validation in parse_safe_domain
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Seed test service user with contact access
        cls.test_service_user = cls.env['res.users'].create({
            'name': 'GraphQL Service User',
            'login': 'graphql_service_user',
            'email': 'service_user@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('base.group_partner_manager').id,
            ])],
        })

        # Seed second test service user for multi-user / isolation tests
        cls.test_service_user_2 = cls.env['res.users'].create({
            'name': 'GraphQL Service User 2',
            'login': 'graphql_service_user_2',
            'email': 'service_user_2@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('base.group_partner_manager').id,
            ])],
        })

        # Seed second key management record for rate-limit and multi-key testing
        cls.service_key_rec_2 = cls.env['dn.graphql.key'].create({
            'name': 'Test Service Gateway Key 2',
            'user_id': cls.test_service_user_2.id,
            'expiration_date': datetime.utcnow() + timedelta(days=30),
        })
        cls.service_key_rec_2.action_generate_key()
        cls.api_key_token_2 = cls.service_key_rec_2.raw_key

        # Seed key management record (dn.graphql.key) for service user
        cls.service_key_rec = cls.env['dn.graphql.key'].create({
            'name': 'Test Service Gateway Key',
            'user_id': cls.test_service_user.id,
            'expiration_date': datetime.utcnow() + timedelta(days=30),
        })
        cls.service_key_rec.action_generate_key()
        cls.api_key_token = cls.service_key_rec.raw_key

        # Seed expired API key for expiration testing
        cls.expired_key_token = cls.env['res.users.apikeys'].with_user(cls.test_service_user).sudo()._generate(
            'graphql', 'Expired Test Key', datetime.utcnow() - timedelta(days=1)
        )

        # Seed wrong scope API key (e.g. 'rpc' scope instead of 'graphql')
        cls.wrong_scope_key_token = cls.env['res.users.apikeys'].with_user(cls.test_service_user).sudo()._generate(
            'rpc', 'Wrong Scope Key', datetime.utcnow() + timedelta(days=30)
        )

        # Seed sample test partner for query tests
        cls.sample_partner = cls.env['res.partner'].create({
            'name': 'GraphQL Sample Test Partner',
            'email': 'sample_test_partner@example.com',
            'phone': '1234567890',
        })

    def _graphql_post(self, query, variables=None, token=None, content_type='application/json', headers=None, data_override=None):
        req_headers = {
            'Content-Type': content_type,
        }
        if token is not None:
            req_headers['Authorization'] = f'Bearer {token}'
        if headers:
            req_headers.update(headers)

        if data_override is not None:
            data = data_override
        elif content_type == 'application/json':
            payload = {'query': query}
            if variables:
                payload['variables'] = variables
            data = json.dumps(payload).encode('utf-8')
        else:
            data = b'binary_payload'

        return self.url_open('/graphql', data=data, headers=req_headers)

    # =========================================================================
    # 1. AUTHENTICATION & HEADER VERIFICATION
    # =========================================================================

    def test_01_auth_missing_header(self):
        """Verify unauthenticated request without Authorization header returns 401 UNAUTHENTICATED."""
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=None)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    def test_02_auth_empty_token(self):
        """Verify request with empty Bearer token returns 401 UNAUTHENTICATED."""
        headers = {'Authorization': 'Bearer '}
        res = self.url_open('/graphql', data=b'{"query": "{ totalCount }"}', headers=headers)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    def test_03_auth_invalid_token(self):
        """Verify request with invalid/fake Bearer token returns 401 UNAUTHENTICATED."""
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token='INVALID_TOKEN_RANDOM_12345')
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    def test_04_auth_expired_key(self):
        """Verify request with expired API key returns 401 KEY_EXPIRED."""
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=self.expired_key_token)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'KEY_EXPIRED')

    def test_05_auth_wrong_scope_key(self):
        """Verify request with API key that has wrong scope (non-graphql) returns 401 UNAUTHENTICATED."""
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=self.wrong_scope_key_token)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    def test_05b_auth_null_scope_key(self):
        """Verify request with API key having scope IS NULL is rejected with 401 UNAUTHENTICATED (TASK-6)."""
        null_scope_token = self.env['res.users.apikeys'].with_user(self.test_service_user).sudo()._generate(
            'graphql', 'Null Scope Key', datetime.utcnow() + timedelta(days=10)
        )
        # Manually force scope to NULL in database
        self.env.cr.execute("UPDATE res_users_apikeys SET scope = NULL WHERE index = %s", (null_scope_token[:8],))
        res = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=null_scope_token)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    # =========================================================================
    # 2. DEACTIVATED / ARCHIVED USER ACCESS BLOCKING (TASK 1 FIX)
    # =========================================================================

    def test_06_auth_deactivated_user_blocked(self):
        """
        Verify security guard: API keys belonging to archived/deactivated users (active=False)
        are immediately rejected with 401 UNAUTHENTICATED.
        """
        user_to_deactivate = self.env['res.users'].create({
            'name': 'Temporary Deactivated User',
            'login': f'temp_deactivated_user_{time.time()}',
            'email': 'temp_deactivated@example.com',
            'active': True,
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        temp_key = self.env['res.users.apikeys'].with_user(user_to_deactivate).sudo()._generate(
            'graphql', 'Deactivation Test Key', datetime.utcnow() + timedelta(days=10)
        )

        # 1. When user is active: key works
        res_active = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=temp_key)
        self.assertEqual(res_active.status_code, 200, "Active user's API key should succeed.")

        # 2. Deactivate the user
        user_to_deactivate.write({'active': False})

        # 3. Same key must now be rejected immediately
        res_deactivated = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=temp_key)
        self.assertEqual(res_deactivated.status_code, 401, "Archived/deactivated user must be denied with 401.")
        body_deactivated = res_deactivated.json()
        self.assertEqual(body_deactivated['errors'][0]['extensions']['code'], 'UNAUTHENTICATED')

    # =========================================================================
    # 3. DYNAMIC DATABASE DETERMINATION & ERROR HANDLING
    # =========================================================================

    def test_07_dynamic_database_missing_error(self):
        """Verify request returns 400 with GRAPHQL_VALIDATION_FAILED when database cannot be determined."""
        from odoo.http import Response
        from ..controllers import main as main_mod

        controller = main_mod.GraphQLController()
        mock_request = MagicMock()
        mock_request.db = False
        mock_request.httprequest.data = b'{"query": "{ totalCount }"}'
        mock_request.httprequest.content_type = 'application/json'
        mock_request.httprequest.headers = {}
        mock_request.make_json_response = lambda payload, status: Response(
            json.dumps(payload), status=status, content_type='application/json'
        )

        with patch.object(main_mod, 'request', mock_request), patch.dict(odoo.tools.config.options, {'db_name': False}):
            res = controller.graphql_endpoint()
            self.assertEqual(res.status_code, 400)
            body = json.loads(res.data)
            self.assertEqual(body['errors'][0]['extensions']['code'], 'GRAPHQL_VALIDATION_FAILED')
            self.assertIn("Database could not be determined", body['errors'][0]['message'])

    # =========================================================================
    # 4. FILE UPLOAD PROHIBITION
    # =========================================================================

    def test_08_upload_multipart_forbidden(self):
        """Verify multipart/form-data upload attempt returns 415 UPLOAD_NOT_ALLOWED."""
        headers = {
            'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundaryXyZ',
            'Authorization': f'Bearer {self.api_key_token}'
        }
        res = self.url_open('/graphql', data=b'fake file upload body', headers=headers)
        self.assertEqual(res.status_code, 415)
        body = res.json()
        self.assertEqual(body['errors'][0]['extensions']['code'], 'UPLOAD_NOT_ALLOWED')

    # =========================================================================
    # 5. SCHEMA GENERATION & QUERY SYNTAX (QUOTED & UNQUOTED)
    # =========================================================================

    def test_09_query_quoted_syntax_and_pagination(self):
        """Verify querying with exact quoted syntax 'res.partner'(first: 3) returns full Relay structure."""
        q = """
        query GetPartners {
            "res.partner"(first: 3) {
                totalCount
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
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
        """
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('data', body)
        self.assertIn('res.partner', body['data'])
        data = body['data']['res.partner']
        self.assertGreaterEqual(data['totalCount'], 1)
        self.assertIn('pageInfo', data)
        self.assertIn('edges', data)
        self.assertTrue(len(data['edges']) > 0)
        self.assertTrue(data['edges'][0]['node']['name'])

    def test_10_query_unquoted_syntax_consistency(self):
        """Verify unquoted syntax res__partner works identically to quoted syntax."""
        q = """
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
        """
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('data', body)
        self.assertIn('res__partner', body['data'])
        self.assertGreaterEqual(body['data']['res__partner']['totalCount'], 1)

    def test_11_lexer_rewriter_unit(self):
        """Unit test lexer rewriter: replaces quoted model identifiers outside literals."""
        src = 'query { "sale.order"(first: 10, domain: "[(\'name\', \'=\', \'sale.order\')]") { edges { node { id } } } }'
        rewritten, mapping = rewrite_quoted_names(src)
        self.assertIn('sale__order(', rewritten)
        self.assertNotIn('"sale.order"', rewritten)
        self.assertIn("[('name', '=', 'sale.order')]", rewritten)
        self.assertEqual(mapping.get('sale__order'), 'sale.order')

        # Test response restoration
        data = {'sale__order': {'edges': [{'node': {'id': 1}}]}}
        restored = restore_names(data, mapping)
        self.assertIn('sale.order', restored)

    # =========================================================================
    # 6. MUTATION CRUD LIFECYCLE & ATOMIC SAVEPOINT ROLLBACK
    # =========================================================================

    def test_12_mutation_crud_lifecycle(self):
        """Verify full Create, Update, Delete mutation lifecycle."""
        # 1. Create
        create_q = """
        mutation {
            "res.partner.create"(values: { name: "GraphQL Lifecycle Partner", email: "lifecycle@example.com" }) {
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
        """
        res_create = self._graphql_post(create_q, token=self.api_key_token)
        self.assertEqual(res_create.status_code, 200)
        body_create = res_create.json()
        self.assertIn('data', body_create)
        node = body_create['data']['res.partner.create']['node']
        self.assertEqual(node['name'], 'GraphQL Lifecycle Partner')
        partner_id = node['id']
        self.assertTrue(partner_id)

        # 2. Update
        update_q = f"""
        mutation {{
            "res.partner.update"(id: {partner_id}, values: {{ name: "GraphQL Lifecycle Partner Updated" }}) {{
                node {{
                    id
                    name
                }}
                userErrors {{
                    message
                }}
            }}
        }}
        """
        res_update = self._graphql_post(update_q, token=self.api_key_token)
        self.assertEqual(res_update.status_code, 200)
        body_update = res_update.json()
        self.assertEqual(body_update['data']['res.partner.update']['node']['name'], 'GraphQL Lifecycle Partner Updated')

        # 3. Delete
        delete_q = f"""
        mutation {{
            "res.partner.delete"(id: {partner_id}) {{
                success
                id
                userErrors {{
                    message
                }}
            }}
        }}
        """
        res_delete = self._graphql_post(delete_q, token=self.api_key_token)
        self.assertEqual(res_delete.status_code, 200)
        body_delete = res_delete.json()
        self.assertTrue(body_delete['data']['res.partner.delete']['success'])

        # Verify record no longer exists
        self.assertFalse(self.env['res.partner'].browse(partner_id).exists())

    def test_13_mutation_atomic_savepoint_rollback(self):
        """
        Verify atomic savepoint rollback:
        When multiple mutations are executed in one request and one fails,
        the ENTIRE request is rolled back. No records are committed.
        """
        unique_name = f"Atomic_Rollback_Target_{time.time()}"
        q = f"""
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
            step2: "res.partner.update"(id: 999999999, values: {{ name: "NonExistent" }}) {{
                node {{
                    id
                }}
                userErrors {{
                    message
                    code
                }}
            }}
        }}
        """
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body.get('extensions', {}).get('rolledBack'), "Expected extensions.rolledBack to be True")

        # Verify step1's record does NOT exist in the database!
        count = self.env['res.partner'].search_count([('name', '=', unique_name)])
        self.assertEqual(count, 0, "Record was committed despite failure! Atomic savepoint rollback failed.")

    # =========================================================================
    # 7. MULTI-TIER DENY / BLOCKLIST (GLOBAL & PER-API KEY)
    # =========================================================================

    def test_14_deny_policy_global_model(self):
        """Verify global blocklist immediately rejects denied models (e.g. ir.model)."""
        q = """
        query {
            "ir.model"(first: 1) {
                totalCount
            }
        }
        """
        res = self._graphql_post(q, token=self.api_key_token)
        self.assertIn(res.status_code, (400, 403))
        body = res.json()
        err_code = body['errors'][0]['extensions']['code']
        self.assertIn(err_code, ('FORBIDDEN_RESOURCE', 'GRAPHQL_VALIDATION_FAILED'))

    def test_15_deny_policy_per_api_key(self):
        """Verify per-API-Key deny policy blocks designated key while allowing other keys."""
        partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

        # Deny res.partner strictly for self.service_key_rec
        deny_rule = self.env['dn.graphql.deny'].create({
            'model_id': partner_model.id,
            'key_rec_id': self.service_key_rec.id,
            'operation': 'read',
            'reason': 'Blocked specifically for service key',
        })

        try:
            # 1. Blocked key fails
            res_blocked = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=self.api_key_token)
            self.assertEqual(res_blocked.status_code, 403)
            self.assertEqual(res_blocked.json()['errors'][0]['extensions']['code'], 'FORBIDDEN_RESOURCE')

            # 2. Other key succeeds
            res_ok = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=self.api_key_token_2)
            self.assertEqual(res_ok.status_code, 200)
        finally:
            deny_rule.unlink()

    # =========================================================================
    # 8. FIELD-LEVEL DENY POLICY
    # =========================================================================

    def test_16_field_level_deny_read(self):
        """Verify field-level deny rule blocks querying restricted fields while allowing others."""
        partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        phone_field = self.env['ir.model.fields'].search([('model_id', '=', partner_model.id), ('name', '=', 'phone')], limit=1)

        deny_rule = self.env['dn.graphql.deny'].create({
            'model_id': partner_model.id,
            'field_id': phone_field.id,
            'key_rec_id': self.service_key_rec.id,
            'operation': 'read',
            'reason': 'Phone field is confidential',
        })

        try:
            # 1. Querying restricted field 'phone' fails with 403
            q_fail = '{ "res.partner"(first: 1) { edges { node { id name phone } } } }'
            res_fail = self._graphql_post(q_fail, token=self.api_key_token)
            self.assertEqual(res_fail.status_code, 403)
            body_fail = res_fail.json()
            self.assertEqual(body_fail['errors'][0]['extensions']['code'], 'FORBIDDEN_RESOURCE')
            self.assertIn("phone", body_fail['errors'][0]['message'])

            # 2. Querying other fields succeeds
            q_ok = '{ "res.partner"(first: 1) { edges { node { id name email } } } }'
            res_ok = self._graphql_post(q_ok, token=self.api_key_token)
            self.assertEqual(res_ok.status_code, 200)
            self.assertIn('data', res_ok.json())
        finally:
            deny_rule.unlink()

    def test_17_field_level_deny_write(self):
        """Verify field-level deny rule blocks modifying restricted fields in mutations."""
        partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        email_field = self.env['ir.model.fields'].search([('model_id', '=', partner_model.id), ('name', '=', 'email')], limit=1)

        deny_rule = self.env['dn.graphql.deny'].create({
            'model_id': partner_model.id,
            'field_id': email_field.id,
            'key_rec_id': self.service_key_rec.id,
            'operation': 'write',
            'reason': 'Email updates blocked for this key',
        })

        try:
            update_q = f"""
            mutation {{
                "res.partner.update"(id: {self.sample_partner.id}, values: {{ email: "new_email@example.com" }}) {{
                    node {{ id }}
                }}
            }}
            """
            res = self._graphql_post(update_q, token=self.api_key_token)
            body = res.json()
            # Mutation savepoint triggers rollback on ForbiddenResourceError
            self.assertTrue(
                res.status_code in (400, 403) or
                bool(body.get('errors')) or
                body.get('extensions', {}).get('rolledBack')
            )
        finally:
            deny_rule.unlink()

    # =========================================================================
    # 9. ANTI-SCRAPING (DEPTH LIMIT, CLAMPING, MAX NODES)
    # =========================================================================

    def test_18_anti_scraping_depth_limit(self):
        """Verify query depth validation rejects nested queries exceeding max_depth."""
        orig_depth = self.env['ir.config_parameter'].sudo().get_param('dn_graphql_gateway.max_depth', '12')
        try:
            # Set depth limit to 2
            self.env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.max_depth', '2')

            # Query with depth 4: query -> res.partner -> edges -> node -> name
            deep_query = '{ "res.partner"(first: 1) { edges { node { id name } } } }'
            res = self._graphql_post(deep_query, token=self.api_key_token)
            self.assertEqual(res.status_code, 400)
            body = res.json()
            self.assertEqual(body['errors'][0]['extensions']['code'], 'GRAPHQL_VALIDATION_FAILED')
            self.assertIn("exceeds configured limit", body['errors'][0]['message'])
        finally:
            self.env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.max_depth', orig_depth)

    def test_19_anti_scraping_max_limit_clamping(self):
        """Verify requested 'first' argument is clamped to max_limit configured for the model."""
        partner_cfg = self.env['dn.graphql.model'].search([('model_name', '=', 'res.partner')], limit=1)
        orig_max = partner_cfg.max_limit
        try:
            # Restrict max_limit to 3
            partner_cfg.write({'max_limit': 3})

            # Create enough dummy records to verify clamping
            for i in range(5):
                self.env['res.partner'].create({'name': f'Clamping Test Partner {i}'})

            q = '{ "res.partner"(first: 100) { edges { node { id } } } }'
            res = self._graphql_post(q, token=self.api_key_token)
            self.assertEqual(res.status_code, 200)
            body = res.json()
            edges = body['data']['res.partner']['edges']
            self.assertLessEqual(len(edges), 3, "Returned edges count must be clamped to max_limit=3.")
        finally:
            partner_cfg.write({'max_limit': orig_max})

    def test_20_anti_scraping_max_nodes_ceiling(self):
        """Verify query exceeding max_nodes config ceiling is rejected with 403 FORBIDDEN_RESOURCE."""
        orig_max_nodes = self.env['ir.config_parameter'].sudo().get_param('dn_graphql_gateway.max_nodes', '1000')
        try:
            # Set ceiling to 1 node
            self.env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.max_nodes', '1')

            # Query requesting 5 records
            q = '{ "res.partner"(first: 5) { edges { node { id } } } }'
            res = self._graphql_post(q, token=self.api_key_token)
            self.assertIn(res.status_code, (400, 403))
            body = res.json()
            err_code = body['errors'][0]['extensions']['code']
            self.assertIn(err_code, ('FORBIDDEN_RESOURCE', 'INTERNAL_SERVER_ERROR'))
        finally:
            self.env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.max_nodes', orig_max_nodes)

    # =========================================================================
    # 10. RATE LIMITING
    # =========================================================================

    def test_21_rate_limiting_exceeded(self):
        """Verify requests exceeding rate limit per minute return HTTP 429 RATE_LIMITED."""
        orig_rate = self.env['ir.config_parameter'].sudo().get_param('dn_graphql_gateway.rate_limit_minute', '60')
        try:
            # Set rate limit to 2 requests per minute
            self.env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.rate_limit_minute', '2')

            q = '{ "res.partner"(first: 1) { totalCount } }'
            # Request 1: success
            r1 = self._graphql_post(q, token=self.api_key_token_2)
            self.assertEqual(r1.status_code, 200)

            # Request 2: success
            r2 = self._graphql_post(q, token=self.api_key_token_2)
            self.assertEqual(r2.status_code, 200)

            # Request 3: must be rate-limited
            r3 = self._graphql_post(q, token=self.api_key_token_2)
            self.assertEqual(r3.status_code, 429)
            body3 = r3.json()
            self.assertEqual(body3['errors'][0]['extensions']['code'], 'RATE_LIMITED')
        finally:
            self.env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.rate_limit_minute', orig_rate)

    # =========================================================================
    # 11. AUDIT LOGGING INDEPENDENCE ACROSS ROLLBACKS & SAVEPOINT
    # =========================================================================

    def test_22_audit_logging_persists_on_success_and_rollback(self):
        """Verify audit log records execution metrics and persists even when a mutation is rolled back."""
        unique_failed_name = f"Log_Rollback_Target_{time.time()}"
        q_fail = f"""
        mutation {{
            step1: "res.partner.create"(values: {{ name: "{unique_failed_name}" }}) {{
                node {{ id }}
            }}
            step2: "res.partner.update"(id: 999999999, values: {{ name: "Fail" }}) {{
                node {{ id }}
                userErrors {{ message code }}
            }}
        }}
        """
        res = self._graphql_post(q_fail, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get('extensions', {}).get('rolledBack'))

        # Search for audit log of this failed mutation
        log = self.env['dn.graphql.log'].search([
            ('user_id', '=', self.test_service_user.id),
            ('query_text', 'like', f'%{unique_failed_name}%')
        ], limit=1)

        self.assertTrue(log, "Audit log must be saved even though mutation rolled back!")
        self.assertTrue(log.rolled_back, "Audit log rolled_back flag must be True")
        self.assertEqual(log.status_code, 200)
        self.assertGreater(log.duration_ms, 0)
        self.assertIn(unique_failed_name, log.request_body)

    def test_22b_audit_log_savepoint_in_transaction(self):
        """Verify DnGraphqlLog.log_request records query metrics using transaction savepoint (TASK-3)."""
        log_vals = {
            'user_id': self.test_service_user.id,
            'query_text': 'query TestSavepointAuditLog { totalCount }',
            'status_code': 200,
            'duration_ms': 15.0,
            'request_body': '{"query": "query TestSavepointAuditLog { totalCount }"}',
            'rolled_back': False,
        }
        self.env['dn.graphql.log'].log_request(self.env, log_vals)
        created_log = self.env['dn.graphql.log'].search([('query_text', '=', 'query TestSavepointAuditLog { totalCount }')], limit=1)
        self.assertTrue(created_log, "Audit log record should be created via env.cr.savepoint()")
        self.assertEqual(created_log.status_code, 200)
        self.assertEqual(created_log.duration_ms, 15.0)

    # =========================================================================
    # 12. SAFE DOMAIN AST VALIDATION & RECURSIVE COMODEL DENY
    # =========================================================================

    def test_23_safe_domain_syntax_error(self):
        """Verify invalid or malformed domain strings return BAD_USER_INPUT."""
        q_bad_domain = '{ "res.partner"(domain: "MALFORMED_INVALID_DOMAIN") { totalCount } }'
        res = self._graphql_post(q_bad_domain, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(bool(body.get('errors')))
        err_code = body['errors'][0]['extensions']['code']
        self.assertEqual(err_code, 'BAD_USER_INPUT')

    def test_24_safe_domain_restricted_field(self):
        """Verify safe domain AST validation blocks filtering on denied fields."""
        partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        vat_field = self.env['ir.model.fields'].search([('model_id', '=', partner_model.id), ('name', '=', 'vat')], limit=1)

        deny_rule = self.env['dn.graphql.deny'].create({
            'model_id': partner_model.id,
            'field_id': vat_field.id,
            'key_rec_id': self.service_key_rec.id,
            'operation': 'read',
            'reason': 'VAT field is confidential',
        })

        try:
            q_vat_filter = '{ "res.partner"(domain: "[(\'vat\', \'!=\', False)]") { totalCount } }'
            res = self._graphql_post(q_vat_filter, token=self.api_key_token)
            body = res.json()
            self.assertTrue(bool(body.get('errors')), "Expected GraphQL execution error for denied domain field")
            err_msg = body['errors'][0]['message']
            self.assertIn("vat", err_msg)
            self.assertIn("restricted", err_msg)
        finally:
            deny_rule.unlink()

    def test_24b_safe_domain_recursive_comodel_deny(self):
        """Verify parse_safe_domain recursively checks relations and blocks queries when comodel fields are denied (TASK-5)."""
        # res.partner -> user_id -> res.users -> password (denied by default in default_deny.xml)
        q = '{ "res.partner"(domain: "[(\'user_id.password\', \'!=\', False)]") { totalCount } }'
        res = self._graphql_post(q, token=self.api_key_token)
        body = res.json()
        self.assertTrue(bool(body.get('errors')), "Expected GraphQL error when filtering on denied comodel field")
        err_msg = body['errors'][0]['message']
        self.assertIn("password", err_msg)
        self.assertIn("restricted", err_msg)

    # =========================================================================
    # 13. API KEY ROTATION MUTATION
    # =========================================================================

    def test_25_rotate_api_key_mutation(self):
        """Verify rotateApiKey mutation invalidates old key and generates functioning new key."""
        rotate_q = """
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
        """
        res = self._graphql_post(rotate_q, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        payload = body['data']['rotateApiKey']
        new_key = payload['newKey']
        self.assertTrue(new_key)
        self.assertTrue(payload['expirationDate'])
        self.assertEqual(len(payload['userErrors']), 0)

        # 1. Old key is immediately invalidated (401)
        res_old = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=self.api_key_token)
        self.assertEqual(res_old.status_code, 401)

        # 2. New key works immediately (200)
        res_new = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=new_key)
        self.assertEqual(res_new.status_code, 200)
        self.assertIn('data', res_new.json())

    # =========================================================================
    # 14. BUSINESS METHOD CALLING & PRIVATE METHOD GUARDRAILS & WHITELIST
    # =========================================================================

    def test_26_call_business_method_success(self):
        """Verify calling model business methods via '<model>.call' and 'callMethod'."""
        partner = self.env['res.partner'].search([], limit=1)

        # 1. Model-specific method call
        q_call = f"""
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
        """
        res = self._graphql_post(q_call, variables={'args': '["read"]'}, token=self.api_key_token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body['data']['res.partner.call']['success'])

        # 2. Dynamic top-level callMethod
        q_generic = f"""
        mutation GenericCall($args: String) {{
            callMethod(model: "res.partner", id: {partner.id}, method: "check_access_rights", args: $args) {{
                success
                result
                userErrors {{
                    message
                }}
            }}
        }}
        """
        res_gen = self._graphql_post(q_generic, variables={'args': '["read"]'}, token=self.api_key_token)
        self.assertEqual(res_gen.status_code, 200)
        self.assertTrue(res_gen.json()['data']['callMethod']['success'])

    def test_27_call_private_method_rejected(self):
        """Verify calling private or internal methods starting with '_' is strictly prohibited."""
        partner = self.env['res.partner'].search([], limit=1)
        q_priv = f"""
        mutation {{
            "res.partner.call"(id: {partner.id}, method: "_compute_display_name") {{
                success
                userErrors {{
                    message
                }}
            }}
        }}
        """
        res = self._graphql_post(q_priv, token=self.api_key_token)
        body = res.json()
        self.assertTrue(
            bool(body.get('errors')) or
            body.get('data', {}).get('res.partner.call') is None or
            body['data']['res.partner.call'].get('success') is False
        )

    def test_27b_call_method_whitelist_guard(self):
        """Verify callMethod is blocked on models not included in active GraphQL whitelist (TASK-4)."""
        currency = self.env['res.currency'].search([], limit=1)
        q = f"""
        mutation GenericCall($args: String) {{
            callMethod(model: "res.currency", id: {currency.id}, method: "check_access_rights", args: $args) {{
                success
                userErrors {{
                    message
                    code
                }}
            }}
        }}
        """
        res = self._graphql_post(q, variables={'args': '["read"]'}, token=self.api_key_token)
        body = res.json()
        self.assertTrue(bool(body.get('errors')), "Expected GraphQL error for non-whitelisted model")
        err_msg = body['errors'][0]['message']
        self.assertIn("not in the active GraphQL whitelist", err_msg)
        self.assertIn(body['errors'][0]['extensions']['code'], ('FORBIDDEN_RESOURCE', 'INTERNAL_SERVER_ERROR'))

    # =========================================================================
    # 15. UI MANAGEMENT LIFECYCLE (dn.graphql.key)
    # =========================================================================

    def test_28_graphql_key_model_lifecycle(self):
        """Verify dn.graphql.key creation, token generation, revoke, and regenerate lifecycle."""
        key_record = self.env['dn.graphql.key'].create({
            'name': 'Lifecycle Management Test Key',
            'user_id': self.test_service_user.id,
            'expiration_date': datetime.utcnow() + timedelta(days=60),
        })
        self.assertEqual(key_record.state, 'draft')
        self.assertFalse(key_record.raw_key)

        # 1. Generate Key
        key_record.action_generate_key()
        self.assertEqual(key_record.state, 'active')
        raw_token = key_record.raw_key
        self.assertTrue(raw_token)
        self.assertTrue(key_record.key_index)

        res1 = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=raw_token)
        self.assertEqual(res1.status_code, 200)

        # 2. Revoke Key
        key_record.action_revoke_key()
        self.assertEqual(key_record.state, 'revoked')
        self.assertFalse(key_record.raw_key)

        res2 = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=raw_token)
        self.assertEqual(res2.status_code, 401)

        # 3. Regenerate Key
        key_record.action_regenerate_key()
        self.assertEqual(key_record.state, 'active')
        new_token = key_record.raw_key
        self.assertTrue(new_token)
        self.assertNotEqual(new_token, raw_token)

        res3 = self._graphql_post('{ "res.partner"(first: 1) { totalCount } }', token=new_token)
        self.assertEqual(res3.status_code, 200)

    # =========================================================================
    # 16. SECURITY HARDENING VERIFICATION (TASK-1, TASK-2)
    # =========================================================================

    def test_29_graphql_key_access_rights_for_standard_user(self):
        """Verify standard internal users (base.group_user) are strictly forbidden from accessing dn.graphql.key (TASK-1)."""
        normal_user = self.env['res.users'].create({
            'name': 'Standard Internal User',
            'login': f'standard_user_{time.time()}',
            'email': 'standard_user@example.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        # 1. Search / Read denied
        with self.assertRaises(AccessError):
            self.env['dn.graphql.key'].with_user(normal_user).search([])

        # 2. Create denied
        with self.assertRaises(AccessError):
            self.env['dn.graphql.key'].with_user(normal_user).create({
                'name': 'Unauthorized Key Record',
                'user_id': normal_user.id,
            })

    def test_30_raw_key_not_stored_in_database(self):
        """Verify raw_key field is not stored in dn_graphql_key table (store=False) (TASK-1)."""
        # 1. Verify model field property
        raw_key_field = self.env['dn.graphql.key']._fields.get('raw_key')
        self.assertFalse(raw_key_field.store, "raw_key field must have store=False")

        # 2. Verify in-memory transient behavior
        key_rec = self.env['dn.graphql.key'].create({
            'name': 'Transient Raw Key Test',
            'user_id': self.test_service_user.id,
        })
        key_rec.action_generate_key()
        self.assertTrue(key_rec.raw_key, "raw_key should be available right after generation in memory")

        # 3. Direct SQL query verifies raw_key is not persisted to database
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'dn_graphql_key' AND column_name = 'raw_key'
        """)
        col_exists = bool(self.env.cr.fetchall())
        if col_exists:
            self.env.cr.execute("SELECT raw_key FROM dn_graphql_key WHERE id = %s", (key_rec.id,))
            row = self.env.cr.fetchone()
            self.assertIsNone(row[0], "raw_key in database table must be NULL/unpersisted!")
        else:
            self.assertFalse(col_exists, "Column raw_key does not exist in dn_graphql_key table")

    def test_31_rate_limiter_atomic_upsert_and_fail_closed(self):
        """Verify check_and_increment uses atomic upsert and fails closed (returns False on DB error) (TASK-2)."""
        RateLimit = self.env['dn.graphql.rate_limit']
        test_index = f"idx_{int(time.time()) % 10000:04d}"
        current_window = int(time.time() // 60)

        # 1. First 2 requests within limit 2 -> True
        self.assertTrue(RateLimit.check_and_increment(self.env.cr, test_index, limit_per_minute=2))
        self.assertTrue(RateLimit.check_and_increment(self.env.cr, test_index, limit_per_minute=2))

        # 2. 3rd request exceeds limit -> False
        self.assertFalse(RateLimit.check_and_increment(self.env.cr, test_index, limit_per_minute=2))

        # 3. Verify DB record exists with request_count == 3
        rec = RateLimit.search([('key_index', '=', test_index), ('window_time', '=', current_window)], limit=1)
        self.assertTrue(rec)
        self.assertEqual(rec.request_count, 3)

        # 4. Fail-closed: database error returns False
        mock_cr = MagicMock()
        mock_cr.savepoint.side_effect = Exception("Simulated DB connection error")
        result = RateLimit.check_and_increment(mock_cr, test_index, limit_per_minute=10)
        self.assertFalse(result, "Rate limiter must fail closed (return False) on database exception")

    # =========================================================================
    # 17. TRANSIENT WIZARD (dn.graphql.key.show)
    # =========================================================================

    def test_action_generate_key_returns_wizard(self):
        """Verify action_generate_key() returns an act_window action for dn.graphql.key.show with default_key."""
        key_rec = self.env['dn.graphql.key'].create({
            'name': 'Generate Key Wizard Action Test',
            'user_id': self.test_service_user.id,
        })
        action = key_rec.action_generate_key()
        self.assertIsInstance(action, dict, "action_generate_key must return a dictionary")
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'dn.graphql.key.show')
        self.assertEqual(action.get('target'), 'new')
        self.assertEqual(action.get('view_mode'), 'form')
        token = action.get('context', {}).get('default_key')
        self.assertTrue(token, "default_key must be present in action context")
        self.assertEqual(token, key_rec.raw_key, "context default_key must match generated raw_key")
        self.assertTrue(token.startswith('dn_key_') or (isinstance(token, str) and len(token) >= 32),
                        "default_key should be a valid API key token")
        self.assertEqual(key_rec.state, 'active')
        self.assertEqual(key_rec.key_index, token[:8])

    def test_action_regenerate_key_returns_wizard(self):
        """Verify action_regenerate_key() returns an act_window action for dn.graphql.key.show with new key."""
        key_rec = self.env['dn.graphql.key'].create({
            'name': 'Regenerate Key Wizard Action Test',
            'user_id': self.test_service_user.id,
        })
        act1 = key_rec.action_generate_key()
        token1 = act1.get('context', {}).get('default_key')
        self.assertTrue(token1)

        act2 = key_rec.action_regenerate_key()
        self.assertIsInstance(act2, dict, "action_regenerate_key must return a dictionary")
        self.assertEqual(act2.get('type'), 'ir.actions.act_window')
        self.assertEqual(act2.get('res_model'), 'dn.graphql.key.show')
        self.assertEqual(act2.get('target'), 'new')
        self.assertEqual(act2.get('view_mode'), 'form')
        token2 = act2.get('context', {}).get('default_key')
        self.assertTrue(token2, "default_key must be present in regenerated action context")
        self.assertNotEqual(token2, token1, "Regenerated key must be different from previous key")
        self.assertEqual(token2, key_rec.raw_key, "context default_key must match regenerated raw_key")
        self.assertTrue(token2.startswith('dn_key_') or (isinstance(token2, str) and len(token2) >= 32),
                        "Regenerated default_key should be a valid API key token")
        self.assertEqual(key_rec.state, 'active')
        self.assertEqual(key_rec.key_index, token2[:8])

    def test_wizard_model_accessible_by_system_user(self):
        """Verify dn.graphql.key.show transient model is accessible by base.group_system and denied for normal users."""
        # 1. User with base.group_system has full access
        system_user = self.env['res.users'].create({
            'name': 'GraphQL System Admin User',
            'login': f'system_user_{time.time()}',
            'email': 'system_user@example.com',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('base.group_system').id,
            ])],
        })
        wizard = self.env['dn.graphql.key.show'].with_user(system_user).create({
            'key': 'test_token_system_access',
        })
        self.assertTrue(wizard.id)
        self.assertEqual(wizard.key, 'test_token_system_access')
        read_res = self.env['dn.graphql.key.show'].with_user(system_user).search([('id', '=', wizard.id)])
        self.assertEqual(len(read_res), 1)

        # 2. Standard user without base.group_system is denied by ACL
        normal_user = self.env['res.users'].create({
            'name': 'Standard Normal User',
            'login': f'normal_user_{time.time()}',
            'email': 'normal_user@example.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            self.env['dn.graphql.key.show'].with_user(normal_user).create({
                'key': 'unauthorized_token',
            })
        with self.assertRaises(AccessError):
            self.env['dn.graphql.key.show'].with_user(normal_user).search([])
