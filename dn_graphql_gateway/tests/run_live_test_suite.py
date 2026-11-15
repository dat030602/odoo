#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
LIVE TEST SUITE RUNNER - dn_graphql_gateway
===============================================================================
Comprehensive automated test runner executing all 6 security & functional test
groups directly against the 'odoo19' database using in-process Odoo Test Client
(Werkzeug dispatch).

Groups Covered:
  Group 1: SQL Injection (SEC-SQL-01 -> SEC-SQL-06)
  Group 2: DDoS / DoS Protection (SEC-DOS-01 -> SEC-DOS-04)
  Group 3: SQL Lỗi & Malformed Domain (MAL-SQL-01 -> MAL-SQL-03)
  Group 4: Block Model & Field Deny Rules (DENY-MOD-01 -> DENY-INF-01)
  Group 5: Model Chưa Whitelist (UNEXP-01 -> UNEXP-02)
  Group 6: Kịch Bản Thành Công / Happy Path (SUC-01 -> SUC-08)

Environment:
  - Database: odoo19
  - Configuration: /tmp/odoo_test.conf
  - PostgreSQL socket: /tmp:5435
===============================================================================
"""

import sys
import os

# Auto-configure search paths
EXTRA_PATHS = ['/tmp/extra_libs', '/opt/odoo19', '/opt/odoo19/dev']
for p in EXTRA_PATHS:
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

import json
import time
import uuid
from datetime import datetime, timedelta

import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from werkzeug.test import Client
from werkzeug.wrappers import Response
import odoo.http as http

CONFIG_FILE = "/tmp/odoo_test.conf"
DATABASE_NAME = "odoo19"


class TestResult:
    def __init__(self, code, name, group, http_status, passed, details=""):
        self.code = code
        self.name = name
        self.group = group
        self.http_status = http_status
        self.passed = passed
        self.details = details


class LiveGraphQLTestSuite:
    def __init__(self, db_name=DATABASE_NAME, conf_path=CONFIG_FILE):
        self.db_name = db_name
        self.conf_path = conf_path
        self.registry = None
        self.client = None
        self.results = []

        # Created test entities tracking for clean teardown
        self.key_master_id = None
        self.key_master_index = None
        self.key_master_token = None
        self.key_restricted_id = None
        self.key_restricted_index = None
        self.key_restricted_token = None
        self.key_spam_id = None
        self.key_spam_index = None
        self.key_spam_token = None
        self.deny_rules = []
        self.created_partner_ids = []

    def init_environment(self):
        """Initializes Odoo config, Registry, and Werkzeug test client."""
        print(f"[*] Initializing Odoo environment with config={self.conf_path}, db={self.db_name}...")
        odoo.tools.config.parse_config(["-c", self.conf_path, "-d", self.db_name])
        self.registry = Registry(self.db_name)
        self.client = Client(http.root, Response)
        print("[+] Registry and HTTP Client successfully initialized.\n")

    def print_existing_data(self):
        """Queries and prints current state of gateway tables and contacts in database."""
        print("=" * 80)
        print("--- EXISTING DATABASE STATE SNAPSHOT (odoo19) ---")
        print("=" * 80)
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # 1. dn.graphql.model
            models = env['dn.graphql.model'].search([])
            print(f"\n[+] Whitelisted GraphQL Models (dn.graphql.model): {len(models)} record(s)")
            for m in models:
                ops = []
                if m.allow_read: ops.append("Read")
                if m.allow_create: ops.append("Create")
                if m.allow_write: ops.append("Write")
                if m.allow_unlink: ops.append("Unlink")
                print(f"    - ID {m.id:2d}: {m.model_name:<20} | Title: {m.name:<15} | Ops: {', '.join(ops)}")

            # 2. dn.graphql.deny
            denies = env['dn.graphql.deny'].search([])
            print(f"\n[+] Active Deny Policies (dn.graphql.deny): {len(denies)} record(s)")
            for d in denies:
                target_str = d.model_name or "ALL"
                if d.field_name:
                    target_str += f".{d.field_name}"
                scope_str = "Global" if d.is_global else f"Key:{d.key_rec_id.name if d.key_rec_id else 'Native'}"
                print(f"    - ID {d.id:2d}: Target: {target_str:<30} | Op: {d.operation:<6} | Scope: {scope_str}")

            # 3. dn.graphql.key
            keys = env['dn.graphql.key'].search([])
            print(f"\n[+] Existing API Keys (dn.graphql.key): {len(keys)} record(s)")
            for k in keys:
                print(f"    - ID {k.id:2d}: Name: {k.name:<30} | User: {k.user_id.name} | State: {k.state} | Prefix: {k.key_index}")

            # 4. res.partner
            partners = env['res.partner'].search([], limit=5)
            partner_count = env['res.partner'].search_count([])
            print(f"\n[+] Contacts (res.partner): Total {partner_count} record(s) (first 5 shown)")
            for p in partners:
                print(f"    - ID {p.id:2d}: Name: {p.name:<30} | Email: {p.email or 'n/a'}")
        print("=" * 80 + "\n")

    def setup_test_data(self):
        """Sets up dedicated test users, keys, and deny policies."""
        print("[*] Setting up isolated test keys and deny policies...")
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            admin_user = env.ref('base.user_admin')
            partner_model = env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

            # 1. Key_Master
            km = env['dn.graphql.key'].create({
                'name': 'Live Suite Key Master',
                'user_id': admin_user.id,
            })
            km.action_generate_key()
            self.key_master_id = km.id
            self.key_master_index = km.key_index
            self.key_master_token = km.raw_key

            # 2. Key_Restricted (denied read on res.partner)
            kr = env['dn.graphql.key'].create({
                'name': 'Live Suite Key Restricted',
                'user_id': admin_user.id,
            })
            kr.action_generate_key()
            self.key_restricted_id = kr.id
            self.key_restricted_index = kr.key_index
            self.key_restricted_token = kr.raw_key

            deny_partner = env['dn.graphql.deny'].create({
                'model_id': partner_model.id,
                'key_rec_id': kr.id,
                'operation': 'read',
                'reason': 'Live Suite Restricted Key - res.partner read forbidden',
            })
            self.deny_rules.append(deny_partner.id)

            # 3. Key_Spam_Test (Rate limiting verification)
            ks = env['dn.graphql.key'].create({
                'name': 'Live Suite Key Spam Test',
                'user_id': admin_user.id,
            })
            ks.action_generate_key()
            self.key_spam_id = ks.id
            self.key_spam_index = ks.key_index
            self.key_spam_token = ks.raw_key

            # 4. Deny read for field 'email' on res.partner (bound to Key_Master)
            email_field = env['ir.model.fields'].search([('model_id', '=', partner_model.id), ('name', '=', 'email')], limit=1)
            deny_email = env['dn.graphql.deny'].create({
                'model_id': partner_model.id,
                'field_id': email_field.id,
                'key_rec_id': km.id,
                'operation': 'read',
                'reason': 'Live Suite - email field read restricted for Key_Master',
            })
            self.deny_rules.append(deny_email.id)

            # 5. Deny write for field 'website' on res.partner (bound to Key_Master)
            website_field = env['ir.model.fields'].search([('model_id', '=', partner_model.id), ('name', '=', 'website')], limit=1)
            deny_website = env['dn.graphql.deny'].create({
                'model_id': partner_model.id,
                'field_id': website_field.id,
                'key_rec_id': km.id,
                'operation': 'write',
                'reason': 'Live Suite - website field write restricted for Key_Master',
            })
            self.deny_rules.append(deny_website.id)

            cr.commit()

        print(f"[+] Test Keys Created:")
        print(f"    - Key_Master:     Index={self.key_master_index}")
        print(f"    - Key_Restricted: Index={self.key_restricted_index}")
        print(f"    - Key_Spam_Test:  Index={self.key_spam_index}")
        print(f"[+] Deny Policies created: {len(self.deny_rules)} rules.\n")

    def cleanup_test_data(self):
        """Cleans up all created test records to ensure zero database pollution."""
        print("\n[*] Starting teardown and cleanup of test fixtures...")
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # Clean created partners
            if self.created_partner_ids:
                pts = env['res.partner'].browse(self.created_partner_ids).exists()
                pts.unlink()
                print(f"[+] Deleted {len(self.created_partner_ids)} test res.partner records.")

            # Clean created deny rules
            if self.deny_rules:
                d_rules = env['dn.graphql.deny'].browse(self.deny_rules).exists()
                d_rules.unlink()
                print(f"[+] Deleted {len(self.deny_rules)} test dn.graphql.deny rules.")

            # Clean test keys
            key_ids_to_del = [kid for kid in (self.key_master_id, self.key_restricted_id, self.key_spam_id) if kid]
            for kid in key_ids_to_del:
                k_rec = env['dn.graphql.key'].browse(kid).exists()
                if k_rec:
                    if k_rec.key_id:
                        k_rec.key_id.unlink()
                    k_rec.unlink()

            # Clean any rotated keys created during SUC-07
            cr.execute("DELETE FROM res_users_apikeys WHERE name LIKE 'Live Suite%' OR name LIKE 'Rotated%'")
            cr.execute("DELETE FROM dn_graphql_key WHERE name LIKE 'Live Suite%'")

            # Clean test rate limit entries
            cr.execute("DELETE FROM dn_graphql_rate_limit WHERE key_index IN (%s, %s, %s)", (
                self.key_master_index or '',
                self.key_restricted_index or '',
                self.key_spam_index or '',
            ))

            cr.commit()
        print("[+] Database teardown complete.\n")

    def post_graphql(self, query, variables=None, token=None, content_type="application/json", raw_data=None):
        """Helper to post GraphQL requests to Werkzeug client."""
        headers = {}
        if token is not None:
            headers['Authorization'] = f"Bearer {token}" if not token.startswith("Bearer ") else token

        if raw_data is not None:
            data = raw_data
        else:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            data = json.dumps(payload)

        headers['Content-Type'] = content_type
        resp = self.client.post("/graphql", data=data, headers=headers, environ_base={'REMOTE_ADDR': '127.0.0.1'})
        resp_text = resp.get_data(as_text=True)
        try:
            body = json.loads(resp_text)
        except Exception:
            body = {"raw": resp_text}
        return resp.status_code, body

    # =========================================================================
    # TEST GROUPS IMPLEMENTATION
    # =========================================================================

    def run_group_1_sql_injection(self):
        print(">>> Executing Group 1: SQL Injection Defense Tests...")
        grp = "Group 1: SQL Injection"

        # SEC-SQL-01: Order clause table drop injection
        q1 = '{ res__partner(first: 2, order: "id; DROP TABLE res_partner;--") { edges { node { id } } } }'
        st1, b1 = self.post_graphql(q1, token=self.key_master_token)
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            table_intact = env['res.partner'].search_count([]) >= 0
        p1 = (st1 in (200, 400)) and bool(b1.get('errors')) and table_intact
        err_msg = (b1.get('errors') or [{}])[0].get('message', '')[:60]
        self.results.append(TestResult("SEC-SQL-01", "Order: DROP TABLE injection", grp, st1, p1, f"ORM rejected: {err_msg}"))

        # SEC-SQL-02: Order clause sleep injection
        t0 = time.time()
        q2 = '{ res__partner(first: 2, order: "id, (SELECT pg_sleep(5))") { edges { node { id } } } }'
        st2, b2 = self.post_graphql(q2, token=self.key_master_token)
        elapsed = time.time() - t0
        p2 = (st2 in (200, 400)) and bool(b2.get('errors')) and elapsed < 4.0
        err_msg = (b2.get('errors') or [{}])[0].get('message', '')[:60]
        self.results.append(TestResult("SEC-SQL-02", "Order: pg_sleep(5) injection", grp, st2, p2, f"Rejected in {elapsed:.2f}s (<4s)"))

        # SEC-SQL-03: Order clause conditional CASE WHEN injection
        q3 = '{ res__partner(first: 2, order: "CASE WHEN (1=1) THEN id ELSE name END") { edges { node { id } } } }'
        st3, b3 = self.post_graphql(q3, token=self.key_master_token)
        p3 = (st3 in (200, 400)) and bool(b3.get('errors'))
        err_msg = (b3.get('errors') or [{}])[0].get('message', '')[:60]
        self.results.append(TestResult("SEC-SQL-03", "Order: CASE WHEN conditional injection", grp, st3, p3, f"ORM rejected: {err_msg}"))

        # SEC-SQL-04: Domain clause injection with DROP TABLE
        q4 = '{ res__partner(first: 2, domain: "[(\'1=1; DROP TABLE res_partner--\', \'=\', 1)]") { edges { node { id } } } }'
        st4, b4 = self.post_graphql(q4, token=self.key_master_token)
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            table_intact = env['res.partner'].search_count([]) >= 0
        p4 = (st4 in (200, 400)) and bool(b4.get('errors')) and table_intact
        err_msg = (b4.get('errors') or [{}])[0].get('message', '')[:60]
        self.results.append(TestResult("SEC-SQL-04", "Domain: DROP TABLE field injection", grp, st4, p4, f"Domain rejected: {err_msg}"))

        # SEC-SQL-05: Domain clause subquery injection
        q5 = '{ res__partner(first: 2, domain: "[(\'id\', \'in\', \'SELECT id FROM res_users\')]") { edges { node { id } } } }'
        st5, b5 = self.post_graphql(q5, token=self.key_master_token)
        p5 = (st5 in (200, 400)) and bool(b5.get('errors'))
        err_msg = (b5.get('errors') or [{}])[0].get('message', '').replace('\n', ' ')[:60]
        self.results.append(TestResult("SEC-SQL-05", "Domain: SELECT subquery in value", grp, st5, p5, f"Subquery treated as literal: {err_msg}"))

        # SEC-SQL-06: Authorization header SQL injection
        q6 = '{ ping }'
        st6, b6 = self.post_graphql(q6, token="Bearer ' OR '1'='1")
        p6 = (st6 == 401) and (b6.get('errors') or [{}])[0].get('extensions', {}).get('code') == 'UNAUTHENTICATED'
        self.results.append(TestResult("SEC-SQL-06", "Auth Header: SQLi bypass Bearer ' OR '1'='1", grp, st6, p6, "HTTP 401 UNAUTHENTICATED returned"))

    def run_group_2_dos_protection(self):
        print(">>> Executing Group 2: DDoS / DoS Protection Tests...")
        grp = "Group 2: DoS Protection"

        # SEC-DOS-01: Spam 65 requests with Key_Spam_Test (Rate limiting: 60 req/min)
        q_spam = '{ "res.partner"(first: 1) { totalCount } }'
        statuses = []
        for i in range(65):
            st, _ = self.post_graphql(q_spam, token=self.key_spam_token)
            statuses.append(st)

        count_200 = statuses.count(200)
        count_429 = statuses.count(429)
        p1 = (count_200 == 60) and (count_429 == 5) and (statuses[60] == 429)
        self.results.append(TestResult(
            "SEC-DOS-01", "Rate Limit: Spam 65 requests", grp, f"200x{count_200}, 429x{count_429}", p1,
            f"Req 1-60 OK (200), Req 61-65 blocked (429 RATE_LIMITED)"
        ))

        # SEC-DOS-02: Query nested 14 levels deep exceeding max_depth (12)
        q_deep = """
        query DeepQuery {
          l1: res__partner(first: 1) {
            l2: edges {
              l3: node {
                l4: company_id {
                  l5: currency_id {
                    l6: country_ids {
                      l7: edges {
                        l8: node {
                          l9: currency_id {
                            l10: country_ids {
                              l11: edges {
                                l12: node {
                                  l13: currency_id {
                                    l14: name
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        st2, b2 = self.post_graphql(q_deep, token=self.key_master_token)
        p2 = (st2 == 400) and "exceeds configured limit" in (b2.get('errors') or [{}])[0].get('message', '')
        self.results.append(TestResult("SEC-DOS-02", "AST Depth: Nested 14 levels (limit 12)", grp, st2, p2, "HTTP 400 GRAPHQL_VALIDATION_FAILED"))

        # SEC-DOS-03: Query exceeding max_nodes ceiling
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            orig_max = env['ir.config_parameter'].sudo().get_param('dn_graphql_gateway.max_nodes', '1000')
            env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.max_nodes', '1')
            cr.commit()

        try:
            q_nodes = '{ res__partner(first: 2) { edges { node { id } } } }'
            st3, b3 = self.post_graphql(q_nodes, token=self.key_master_token)
            p3 = (st3 in (400, 403)) and "max" in (b3.get('errors') or [{}])[0].get('message', '').lower()
            self.results.append(TestResult("SEC-DOS-03", "Node Ceiling: Exceeding max_nodes (1 node)", grp, st3, p3, "HTTP 403 FORBIDDEN_RESOURCE"))
        finally:
            with self.registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['ir.config_parameter'].sudo().set_param('dn_graphql_gateway.max_nodes', orig_max)
                cr.commit()

        # SEC-DOS-04: Multipart/form-data upload attempt
        st4, b4 = self.post_graphql(
            "", token=self.key_master_token,
            content_type="multipart/form-data; boundary=----WebKitFormBoundaryXYZ",
            raw_data=b"fake file payload"
        )
        p4 = (st4 == 415) and (b4.get('errors') or [{}])[0].get('extensions', {}).get('code') == 'UPLOAD_NOT_ALLOWED'
        self.results.append(TestResult("SEC-DOS-04", "Upload Prohibition: multipart/form-data", grp, st4, p4, "HTTP 415 UPLOAD_NOT_ALLOWED"))

    def run_group_3_malformed_sql(self):
        print(">>> Executing Group 3: SQL Lỗi & Malformed Domain Tests...")
        grp = "Group 3: Malformed SQL & Domain"

        # MAL-SQL-01: Malformed domain syntax
        q1 = '{ res__partner(first: 2, domain: "MALFORMED_INVALID_DOMAIN") { edges { node { id } } } }'
        st1, b1 = self.post_graphql(q1, token=self.key_master_token)
        code1 = (b1.get('errors') or [{}])[0].get('extensions', {}).get('code', '')
        p1 = (st1 in (200, 400)) and (code1 == 'BAD_USER_INPUT' or bool(b1.get('errors')))
        self.results.append(TestResult("MAL-SQL-01", "Domain Syntax: Invalid AST token string", grp, st1, p1, f"Code: {code1}"))

        # MAL-SQL-02: Non-existent comodel in dot-traversal
        q2 = '{ res__partner(first: 2, domain: "[(\'non_existent_comodel.name\', \'=\', \'test\')]") { edges { node { id } } } }'
        st2, b2 = self.post_graphql(q2, token=self.key_master_token)
        p2 = (st2 in (200, 400)) and bool(b2.get('errors')) and "Invalid field" in (b2.get('errors') or [{}])[0].get('message', '')
        self.results.append(TestResult("MAL-SQL-02", "Domain Comodel: non_existent_comodel.name", grp, st2, p2, "Field existence checked safely"))

        # MAL-SQL-03: Invalid operator in domain
        q3 = '{ res__partner(first: 2, domain: "[(\'name\', \'INVALID_OP\', \'test\')]") { edges { node { id } } } }'
        st3, b3 = self.post_graphql(q3, token=self.key_master_token)
        p3 = (st3 in (200, 400)) and bool(b3.get('errors')) and "Invalid operator" in (b3.get('errors') or [{}])[0].get('message', '')
        self.results.append(TestResult("MAL-SQL-03", "Domain Operator: INVALID_OP operator", grp, st3, p3, "Invalid operator rejected"))

    def run_group_4_deny_rules(self):
        print(">>> Executing Group 4: Block Model & Field Deny Rules Tests...")
        grp = "Group 4: Deny Rules"

        # DENY-MOD-01: Query ir__model (global default deny)
        q1 = '{ ir__model(first: 1) { totalCount } }'
        st1, b1 = self.post_graphql(q1, token=self.key_master_token)
        p1 = (st1 in (400, 403)) and bool(b1.get('errors'))
        self.results.append(TestResult("DENY-MOD-01", "Model Deny: Global deny on ir.model", grp, st1, p1, "HTTP 400/403 blocked from schema/query"))

        # DENY-MOD-02: Query res__partner with Key_Restricted vs Key_Master
        q2 = '{ res__partner(first: 1) { totalCount } }'
        st2_r, b2_r = self.post_graphql(q2, token=self.key_restricted_token)
        st2_m, b2_m = self.post_graphql(q2, token=self.key_master_token)
        p2 = (st2_r == 403) and (st2_m == 200) and ((b2_r.get('errors') or [{}])[0].get('extensions', {}).get('code') == 'FORBIDDEN_RESOURCE')
        self.results.append(TestResult("DENY-MOD-02", "Model Deny: Key_Restricted blocked vs Master OK", grp, f"Restricted: {st2_r}, Master: {st2_m}", p2, "Per-key policy strictly enforced"))

        # DENY-FLD-01: Query restricted field 'email' on Key_Master
        q3 = '{ res__partner(first: 1) { edges { node { id email } } } }'
        st3, b3 = self.post_graphql(q3, token=self.key_master_token)
        p3 = (st3 == 403) and (b3.get('errors') or [{}])[0].get('extensions', {}).get('code') == 'FORBIDDEN_RESOURCE'
        self.results.append(TestResult("DENY-FLD-01", "Field Deny Read: Field 'email' query", grp, st3, p3, "HTTP 403 FORBIDDEN_RESOURCE"))

        # DENY-FLD-02: Mutation update restricted field 'website' on Key_Master
        q4 = 'mutation { "res.partner.update"(id: 1, values: { website: "https://example.com" }) { node { id } userErrors { message code } } }'
        st4, b4 = self.post_graphql(q4, token=self.key_master_token)
        p4 = (st4 == 403) or (b4.get('extensions', {}).get('rolledBack') is True and "website" in str(b4.get('errors')))
        self.results.append(TestResult("DENY-FLD-02", "Field Deny Write: Mutation update 'website'", grp, st4, p4, "Rolled back & write denied"))

        # DENY-INF-01: Inferred comodel traversal user_id.password
        q5 = '{ res__partner(first: 1, domain: "[(\'user_id.password\', \'!=\', False)]") { totalCount } }'
        st5, b5 = self.post_graphql(q5, token=self.key_master_token)
        err_msg = (b5.get('errors') or [{}])[0].get('message', '')
        p5 = (st5 in (200, 403)) and ("password" in err_msg and "restricted" in err_msg)
        self.results.append(TestResult("DENY-INF-01", "Comodel Traversal: user_id.password in domain", grp, st5, p5, "Denied comodel traversal blocked"))

    def run_group_5_unexposed_models(self):
        print(">>> Executing Group 5: Model Chưa Whitelist Tests...")
        grp = "Group 5: Whitelist Isolation"

        # UNEXP-01: Query res__currency (not whitelisted)
        q1 = '{ res__currency(first: 2) { edges { node { id } } } }'
        st1, b1 = self.post_graphql(q1, token=self.key_master_token)
        p1 = (st1 == 400) and "Cannot query field 'res__currency'" in (b1.get('errors') or [{}])[0].get('message', '')
        self.results.append(TestResult("UNEXP-01", "Query Unexposed: res__currency not whitelisted", grp, st1, p1, "HTTP 400 Schema validation rejected"))

        # UNEXP-02: Mutation callMethod on res.users (not whitelisted)
        q2 = """
        mutation CallUsers($args: String) {
            callMethod(model: "res.users", id: 1, method: "check_access_rights", args: $args) {
                success
                result
                userErrors { message code }
            }
        }
        """
        st2, b2 = self.post_graphql(q2, variables={"args": '["read"]'}, token=self.key_master_token)
        err_msg = str(b2.get('errors', []))
        p2 = (st2 in (200, 403)) and "not in the active GraphQL whitelist" in err_msg
        self.results.append(TestResult("UNEXP-02", "callMethod Unexposed: res.users whitelist guard", grp, st2, p2, "Whitelisting guard blocked method call"))

    def run_group_6_success_scenarios(self):
        print(">>> Executing Group 6: Kịch Bản Thành Công (Happy Path)...")
        grp = "Group 6: Success Scenarios"

        # SUC-01: Relay pagination res__partner(first: 3)
        q1 = '{ res__partner(first: 3) { totalCount pageInfo { hasNextPage startCursor endCursor } edges { cursor node { id name } } } }'
        st1, b1 = self.post_graphql(q1, token=self.key_master_token)
        data1 = (b1.get('data') or {}).get('res__partner', {})
        p1 = (st1 == 200) and ('pageInfo' in data1) and ('edges' in data1)
        self.results.append(TestResult("SUC-01", "Relay Pagination: res__partner(first: 3)", grp, st1, p1, f"totalCount={data1.get('totalCount')}, edges={len(data1.get('edges', []))}"))

        # SUC-02: Domain filter [('is_company', '=', True)]
        q2 = '{ res__partner(first: 2, domain: "[(\'is_company\', \'=\', True)]") { totalCount edges { node { id name is_company } } } }'
        st2, b2 = self.post_graphql(q2, token=self.key_master_token)
        data2 = (b2.get('data') or {}).get('res__partner', {})
        p2 = (st2 == 200) and ('edges' in data2)
        self.results.append(TestResult("SUC-02", "Domain Filter: [('is_company', '=', True)]", grp, st2, p2, f"Returned {len(data2.get('edges', []))} companies"))

        # SUC-03: Quoted syntax "res.partner"(first: 2)
        q3 = '{ "res.partner"(first: 2) { totalCount edges { node { id name } } } }'
        st3, b3 = self.post_graphql(q3, token=self.key_master_token)
        data3 = (b3.get('data') or {}).get('res.partner', {})
        p3 = (st3 == 200) and ('edges' in data3)
        self.results.append(TestResult("SUC-03", "Quoted Model Syntax: \"res.partner\"", grp, st3, p3, "Quoted name restored in JSON data"))

        # SUC-04: Mutation Create Partner
        unique_name = f"QA Live Suite Partner {int(time.time())}"
        q4 = """
        mutation CreateP($name: String!) {
            "res.partner.create"(values: { name: $name }) {
                node { id name }
                userErrors { message code }
            }
        }
        """
        st4, b4 = self.post_graphql(q4, variables={"name": unique_name}, token=self.key_master_token)
        node4 = (b4.get('data') or {}).get('res.partner.create', {}).get('node')
        new_partner_id = node4.get('id') if node4 else None
        if new_partner_id:
            self.created_partner_ids.append(new_partner_id)
        p4 = (st4 == 200) and (new_partner_id is not None)
        self.results.append(TestResult("SUC-04", "Mutation Create: New partner record", grp, st4, p4, f"Created Partner ID={new_partner_id}"))

        # SUC-05: Mutation Update Partner
        if new_partner_id:
            updated_name = f"{unique_name} [Updated]"
            q5 = f"""
            mutation UpdateP {{
                "res.partner.update"(id: {new_partner_id}, values: {{ name: "{updated_name}" }}) {{
                    node {{ id name }}
                    userErrors {{ message code }}
                }}
            }}
            """
            st5, b5 = self.post_graphql(q5, token=self.key_master_token)
            node5 = (b5.get('data') or {}).get('res.partner.update', {}).get('node')
            p5 = (st5 == 200) and (node5.get('name') == updated_name)
            self.results.append(TestResult("SUC-05", "Mutation Update: Partner name modification", grp, st5, p5, f"Updated Name='{updated_name}'"))
        else:
            self.results.append(TestResult("SUC-05", "Mutation Update: Partner name modification", grp, 0, False, "Skipped due to SUC-04 failure"))

        # SUC-06: Mutation Delete Partner
        if new_partner_id:
            q6 = f"""
            mutation DeleteP {{
                "res.partner.delete"(id: {new_partner_id}) {{
                    success
                    id
                    userErrors {{ message code }}
                }}
            }}
            """
            st6, b6 = self.post_graphql(q6, token=self.key_master_token)
            del_data = (b6.get('data') or {}).get('res.partner.delete', {})
            p6 = (st6 == 200) and (del_data.get('success') is True)
            self.results.append(TestResult("SUC-06", "Mutation Delete: Partner record unlinking", grp, st6, p6, f"Deleted ID={del_data.get('id')}"))
        else:
            self.results.append(TestResult("SUC-06", "Mutation Delete: Partner record unlinking", grp, 0, False, "Skipped due to SUC-04 failure"))

        # SUC-07: In-place API Key Rotation
        q7 = """
        mutation RotateKey {
            rotateApiKey(expiresInDays: 30) {
                newKey
                expirationDate
                userErrors { message code }
            }
        }
        """
        # Create a disposable key for rotation test
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            admin_user = env.ref('base.user_admin')
            rot_key_rec = env['dn.graphql.key'].create({
                'name': 'Live Suite Key For Rotation',
                'user_id': admin_user.id,
            })
            rot_key_rec.action_generate_key()
            rot_token = rot_key_rec.raw_key
            cr.commit()

        st7, b7 = self.post_graphql(q7, token=rot_token)
        new_key_token = (b7.get('data') or {}).get('rotateApiKey', {}).get('newKey')

        if new_key_token:
            # Verify old key is invalidated (401)
            st_old, _ = self.post_graphql('{ ping }', token=rot_token)
            # Verify new key works (200)
            st_new, b_new = self.post_graphql('{ "res.partner"(first: 1) { totalCount } }', token=new_key_token)
            p7 = (st7 == 200) and (st_old == 401) and (st_new == 200)
            details7 = f"Rotated Token={new_key_token[:8]}..., Old Key=401, New Key=200"
        else:
            p7 = False
            details7 = f"Failed to rotate key: {b7}"

        self.results.append(TestResult("SUC-07", "Key Rotation: In-place rotateApiKey", grp, st7, p7, details7))

        # SUC-08: Business Method Call check_access_rights
        q8 = """
        mutation CallAccessRights($args: String) {
            "res.partner.call"(id: 1, method: "check_access_rights", args: $args) {
                success
                result
                userErrors { message code }
            }
        }
        """
        st8, b8 = self.post_graphql(q8, variables={"args": '["read"]'}, token=self.key_master_token)
        call_res = (b8.get('data') or {}).get('res.partner.call', {})
        p8 = (st8 == 200) and (call_res.get('success') is True)
        self.results.append(TestResult("SUC-08", "Method Call: check_access_rights on res.partner", grp, st8, p8, f"Call Success={call_res.get('success')}"))

    def display_report(self):
        """Prints a well-formatted test report table and final summary."""
        print("\n" + "=" * 105)
        print(f"{'LIVE TEST EXECUTION REPORT':^105}")
        print("=" * 105)
        header = f"{'CODE':<12} | {'SCENARIO NAME':<38} | {'HTTP':<14} | {'RESULT':<8} | {'DETAILS'}"
        print(header)
        print("-" * 105)

        current_grp = ""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        for r in self.results:
            if r.group != current_grp:
                current_grp = r.group
                print(f"\n--- {current_grp} ---")
            status_str = str(r.http_status) if r.http_status != 0 else "N/A"
            res_str = "PASS" if r.passed else "FAIL"
            print(f"{r.code:<12} | {r.name:<38} | {status_str:<14} | {res_str:<8} | {r.details}")

        print("=" * 105)
        print(f"TOTAL: {total_tests} tests  |  PASSED: {passed_tests}  |  FAILED: {failed_tests}")
        print("=" * 105)

        if failed_tests == 0:
            print("RESULT: PASS")
            print(f"Unit: {total_tests} tests, 0 failed")
            print("STATUS: SUCCESS")
            return 0
        else:
            print("RESULT: FAIL")
            print(f"Unit: {total_tests} tests, {failed_tests} failed")
            print("STATUS: FAILED")
            return 1

    def run(self):
        start_time = time.time()
        try:
            self.init_environment()
            self.print_existing_data()
            self.setup_test_data()

            self.run_group_1_sql_injection()
            self.run_group_2_dos_protection()
            self.run_group_3_malformed_sql()
            self.run_group_4_deny_rules()
            self.run_group_5_unexposed_models()
            self.run_group_6_success_scenarios()

        except Exception as e:
            print(f"\n[!] Unexpected Error during test execution: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            self.cleanup_test_data()
            duration = time.time() - start_time
            print(f"[*] Total Execution Time: {duration:.2f} seconds")

        return self.display_report()


if __name__ == "__main__":
    runner = LiveGraphQLTestSuite()
    sys.exit(runner.run())
