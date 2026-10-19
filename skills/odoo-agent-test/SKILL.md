---
name: odoo-agent-test
description: >-
  Use when writing, running, or verifying tests for an Odoo module. Integrates native
  Odoo unit tests (TransactionCase/HttpCase) with GraphQL API live verification
  and dn.graphql.log audit inspection. Never creates external test scripts or modifies
  production code.
---

# Odoo Agentic Testing Workflow

Scope: You may only create/edit native test files in `<module>/tests/`.
Production code (models, views, security, data) belongs to `odoo-coder`.
**NEVER** create external test scripts (`scripts/run_test.py`, `scripts/odoo_rpc.py`) or modify module files with auxiliary scripts.
Use Python: `/opt/venv312/bin/python3.12 /opt/odoo19/odoo-bin -c /opt/odoo19.conf`

---

## 0. Inputs and Safety
- Needed: Odoo version, module name, DB name, port, API key (Bearer token from `dn.graphql.key`).
- The DB MUST be a test/dev database. If the name suggests production (prod, live, main) or the user has not confirmed it is disposable, STOP and ask.
- NEVER write credentials into git commits or public logs. Use environment variables (`ODOO_API_KEY`, `ODOO_URL`) or keys managed in `dn.graphql.key`.
- Every test record created must have a `ZZTEST_` prefix in name/reference so it can be identified and cleaned up.

---

## 1. Mode A — Write Native Tests First (Before Coding / Bug Reproduction)
1. Read the approved `docs/analysis/<feature>.md` (or the bug report). If not approved -> STOP.
2. Map every `AC-n` to at least one test named `test_ac<n>_<behavior>`. Register files in `tests/__init__.py`.
3. Base classes:
   - `odoo.tests.common.TransactionCase` for CRUD, business methods, constraints, and ACLs (default choice).
   - `odoo.tests.common.HttpCase` only for controllers, website endpoints, or tours.
4. Cover: CRUD, business workflows, exceptions (`assertRaises(ValidationError/AccessError/UserError)`), access per security group (`with_user()`), multi-company isolation.
5. Seed data in `setUpClass`: 1 extra company and 2 test users in distinct security groups (use `Command.create()`). No reliance on demo data.
6. Run native tests (Section 2). Tests MUST fail, and fail for the right reason (missing feature/behavior), not syntax or setup errors.

---

## 2. Run Native Tests (Source of Truth for CI & Code Coverage)
```bash
coverage run --source=<path/to/module> /opt/venv312/bin/python3.12 /opt/odoo19/odoo-bin \
  -c /opt/odoo19.conf -d <db> -u <module> \
  --test-enable --test-tags /<module> --stop-after-init --http-port=<port>
coverage report -m
```
- **Target:** 80%+ line coverage of the module's Python files (excluding `__manifest__.py`, migrations).
- Report real coverage numbers; if below target, list uncovered methods and add tests.
- Before final sign-off, run the full test suite of the module and any module depending on it.

---

## 3. Live-Server Verification via GraphQL API Gateway & Audit Logs (`dn.graphql.log`)

> **CORE PRINCIPLE:** Do NOT create or run auxiliary external scripts (`scripts/run_test.py`, `scripts/odoo_rpc.py`).
> All mock data creation, verification querying, business workflow execution, and result inspection are performed directly by **sending GraphQL API requests (`/graphql`)** and **inspecting audit logs (`dn.graphql.log`)**.

### 3.1. Authentication with API Keys (`dn.graphql.key`)
- Use the Bearer token provisioned for the Service User matching the required security group (e.g., `Sales API Service User`, `Warehouse Scanner Service User`, `Purchase Service User`).
- Endpoint: `POST http://localhost:<port>/graphql`
- Headers:
  - `Authorization: Bearer <API_KEY>`
  - `Content-Type: application/json`

### 3.2. GraphQL Testing Lifecycle

1. **Create Mock Data:**
   - Execute mutation with `ZZTEST_` prefix:
   ```graphql
   mutation {
     <model>__create(values: { name: "ZZTEST_Record_01", ... }) {
       node { id name ... }
       userErrors { message field code }
     }
   }
   ```
2. **Query & Select Data:**
   - Execute connection query to verify records, quantities, and nested relations:
   ```graphql
   query {
     <model>(domain: "[('name', '=like', 'ZZTEST_%')]", first: 10) {
       totalCount
       edges {
         node { id name ... }
       }
     }
   }
   ```
3. **Execute Business Workflows (Method Calls):**
   - Call mutation `callMethod` or `<model>__call` to trigger workflows (e.g. `action_confirm`, `button_validate`, etc.):
   ```graphql
   mutation {
     callMethod(model: "<model>", method: "<business_method>", id: <record_id>, kwargs: "{}") {
       success
       result
       userErrors { message field code }
     }
   }
   ```
4. **Teardown Mock Data:**
   - Delete all created `ZZTEST_` records using the delete mutation:
   ```graphql
   mutation {
     <model>__delete(id: <record_id>) {
       success
       userErrors { message }
     }
   }
   ```

### 3.3. Audit Log Inspection & Verification (`dn.graphql.log`)
After each request or test scenario:
1. Cross-reference the audit log record in `dn.graphql.log` (via Odoo UI menu **GraphQL Gateway > Request Logs** or ORM search):
   - **`status_code`**: Must be `200` for valid cases, or `400`/`403` when testing security/deny blocks.
   - **`user_id`**: Confirms execution under the exact Service User context (validating Odoo ACLs and Record Rules).
   - **`duration_ms`**: Tracks response latency and execution performance.
   - **`request_body` & `response_body`**: Pre-formatted JSON with indentation for easy payload inspection and result verification.
2. If an error occurs, inspect `errors` or `response_body` in the log immediately without grepping terminal outputs.

---

## 4. When Something Fails
- **Test Defect (bad syntax, wrong assertion):** Fix the query or test assertion, and re-run (maximum 3 iterations).
- **Module Defect or Odoo Traceback:** Report to `odoo-coder` with test name, traceback/error excerpt from `dn.graphql.log`, affected AC ID, and probable cause.
- **NEVER** weaken, skip, or remove assertions to artificially make tests pass.

---

## 5. Cleanup and Reporting
- Ensure no temporary script files are left in the repository.
- Final report format:
```markdown
Mode: A|B     Result: PASS|FAIL
Native Tests: <n> tests, <n> failed     Coverage: <xx>% (Target: 80%+)
GraphQL API Tests: <n> requests (Create / Select / Call / Delete)
Audit Log Status: Verified in dn.graphql.log (Status: 200, User: <user_name>, Avg Duration: <ms>)
AC Mapping:
  - AC-1 -> test_ac1_... OK | FAIL
  - AC-2 -> GraphQL API callMethod OK | FAIL
Failures (if any): <error excerpt from dn.graphql.log>
Files changed: <list of files in tests/>
```