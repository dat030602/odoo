# AGENTS.md — Odoo 19 Multi-Agent, Deep-Thinking & MCP Orchestration Rules (Antigravity)

## 0. COGNITIVE ENGINE & ANTI-HALLUCINATION PROTOCOL (MANDATORY FIRST STEP)

Before routing to ANY subagent or writing a single line of code/prose, the Agent MUST execute a structured **Thinking & Grounding Block**. "Eager execution" (jumping straight into code generation or guessing Odoo behaviors from training memory) is **STRICTLY FORBIDDEN**.

### 0.1. The "Evidence-Before-Action" Law
1. **No Blind Claims:** You are forbidden from stating that a model, field, method, or XML `xpath` target exists in Odoo 19 without first calling `odoo-core-source` (filesystem) or `odoo-rpc` / `odoo-postgres` to verify it.
2. **Mandatory Explainability Blueprint:** Whether answering a functional question (Route B) or planning a feature (Route A), always expose your reasoning clearly to the user:
   - **Why** this architectural approach was chosen over alternatives.
   - **Which** exact core files (`/opt/odoo19/addons/...`) and base methods were inspected.
   - **What** trade-offs exist (ORM performance, upgrade safety, multi-company impact).
3. **Model Switching Strategy (Antigravity Pro Optimization):**
   - **Architecture, Planning, Complex ORM/OWL & Final Verification (Phases 1, 2, 4):** Prioritize deep reasoning & strict tool-calling discipline.
   - **Boilerplate Expansion, Source Scanning & Documentation (Phases 3, 5):** Follow the locked specification in `docs/analysis/<feature>.md` with 0% deviation.

---

## 1. Intent-Based Routing Gate & Autonomous Execution

### 1.1. Three-Way Autonomous Routing Protocol
Analyze the user's prompt intent first and route autonomously:

- **ROUTE A — Module Development, Logic Changes & Code Modifications:**
  *Trigger:* Creating a new Odoo module, modifying business models/views, writing logic (computed fields, constraints, methods, cron jobs, OWL components), or fixing bugs.
  -> **Execute the `odoo-code` Main Agent** (`.agents/agents/odoo-code.md`).
  The `odoo-code` orchestrator coordinates the specialized subagents in sequence with **strict file-based handoffs**:
  1. `odoo-analyst`: Grounded functional/technical analysis via MCPs, Acceptance Criteria, Context Brief tracing -> writes `docs/analysis/<feature>.md`.
  2. `odoo-tester`: TDD Red phase test creation -> `<module>/tests/` -> confirm failure via Terminal/RPC.
  3. `odoo-coder`: Implementation strictly following approved `docs/analysis/<feature>.md` until tests pass; resolves Blocker/Major review findings.
  4. `odoo-tester`: Regression, coverage (80%+), real-data seeding & API verification via `dev/dn_graphql_gateway` (Zero Errors required), MCP `odoo-rpc` / `odoo-postgres`, Terminal module upgrade check, and interactive UI verification via `playwright` + `chrome-devtools`.
  5. `odoo-reviewer`: Automated code review against Odoo 19 conventions, security, performance, and upgrade safety -> writes `docs/review/<feature>.md`.
  6. **Double-Check Gate**: Verify all ACs, zero console/terminal errors, and hygiene checks before delivery.

- **ROUTE B — Functional Consulting, Business Process Analysis & Live System Inspection (No Code Changes):**
  *Trigger:* Questions about Odoo 19 functional workflows (Accounting, Inventory, Manufacturing, Sales, etc.), "how does X work in Odoo?", business requirement mapping, Gap Analysis (Fit/Gap), or live database data inspection.
  -> **Execute the `Functional & Architecture Advisory Protocol`:**
  1. **Ground in Core & Live DB:** Automatically call `odoo-core-source` to read the actual Odoo 19 addon logic AND call `odoo-rpc` (`fields_get`, `search_read`) or `odoo-postgres` to inspect the live configuration/data.
  2. **Select Specialized Subagent:** Invoke `business-analyst`, `architect-reviewer`, or `postgres-pro` (from the 167 community subagents) with relevant skills (`odoo-19`, `architecture-review`).
  3. **Structured Explanation Output:** Present the answer using a rigorous structure:
     - **Standard Odoo 19 Behavior:** How core Odoo handles this out-of-the-box (citing exact models/methods/views).
     - **Live Environment State:** What is currently configured in `odoo19` (via MCP evidence).
     - **Fit/Gap & Recommendation:** Configuration vs. Customization trade-offs.

- **ROUTE C — DevOps, Database Optimization, Security Audit & General Engineering:**
  *Trigger:* PostgreSQL tuning, Docker setup, MCP troubleshooting, security auditing, API design, or documentation tasks.
  -> **Autonomously select the best-matching Community Subagent** (`postgres-pro`, `security-auditor`, `docker-expert`, `technical-writer`, `api-designer`, etc.) via `invoke_subagent`.
  -> **Mandatory Double-Check**: `odoo-code` cross-verifies the subagent's output against Odoo 19 environment standards before presenting the final answer.

---

### 1.2. Core Execution Principles (Anti-Shortcut Rules)
- **No Monolithic Coding:** The Main Agent **MUST NEVER** write all code directly in a single pass without creating or updating `docs/analysis/<feature>.md` first.
- **No Simulated Tool Calls:** Never pretend a test passed or a view rendered cleanly. Every verification claim must be backed by actual Terminal output, `odoo-rpc` response, or `chrome-devtools` log.
- **Shared Handoff Files (`docs/analysis/<feature>.md` and `docs/review/<feature>.md`) are the Single Source of Truth** for state and deliverables passed between agents.

---

## 2. Subagent Delegation Matrix (Subagents, Skills & MCP)

| Phase | Subagent (`VoltAgent`) | Skills (`unclecatvn` / AAS) | Authorized MCP Servers | Primary MCP Responsibilities | Write Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Analysis, Functional & Design** | `business-analyst`<br>*(or `architect-reviewer`)* | `odoo-19` (`models-orm`, `views-actions`, `security`, `api-highlights`), `architecture-review` | • `odoo-core-source`<br>• `context7`<br>• `fetch-docs`<br>• `odoo-postgres`<br>• `odoo-rpc` | • Inspect base source code in `/opt/odoo19/addons` to design proper inheritance (`_inherit`) & explain standard flows.<br>• Query `odoo-rpc` (`fields_get`) & `odoo-postgres` to inspect live schema.<br>• Query official Odoo 19 / OWL docs via `context7` & `fetch-docs`. | `docs/analysis/<feature>.md` |
| **2. Testing (TDD, RPC & UI)** | `qa-expert`<br>*(or `test-automator`)* | `odoo-ui-verify`, `odoo-automated-tests`, `odoo-19` (`testing`) | • `playwright`<br>• `chrome-devtools`<br>• `odoo-rpc`<br>• `odoo-postgres`<br>• `dn_graphql_gateway` | • **`dn_graphql_gateway`** (`/opt/odoo19/dev/dn_graphql_gateway`): Seed real test data via GraphQL mutations and verify queries. Zero errors required for PASS.<br>• **`playwright`**: Automated login, button clicks, Form/Wizard execution (E2E action via Accessibility Tree).<br>• **`chrome-devtools`**: Capture JS/OWL console errors, inspect `call_kw` network requests, and record visual evidence.<br>• **`odoo-rpc` & `odoo-postgres`**: Seed test data and verify backend database state. | `<module>/tests/`, `scripts/run_test.py`, `docs/review/screenshots/` |
| **3. Implementation (Backend & UI)** | `backend-developer` / `python-pro`<br>*(paired with `frontend-developer` for OWL/JS)* | `odoo-19` (`models-orm`, `decorators`, `views-actions`, `owl-frontend`, `security`, `controllers`, `performance`), `odoo-workflow` | • `odoo-core-source`<br>• `context7`<br>• `fetch-docs`<br>• `odoo-postgres` | • **`odoo-core-source`**: Inspect core base methods before calling `super()`; locate accurate `xpath` targets.<br>• **`context7`**: Retrieve latest OWL 2 and Odoo 19 ORM syntax.<br>• **`odoo-postgres`**: Inspect `ir_ui_view` and `ir_model_fields` during debugging. | `<module>/models/`, `views/`, `security/`, `controllers/`, `data/`, `wizard/`, `static/src/` |
| **4. Code Review & Verification** | `code-reviewer` / `odoo-code-review`<br>*(paired with `architect-reviewer`)* | `odoo-19` (`performance`, `security`, `models-orm`, `api-highlights`, `migrations`), `code-review`, `odoo-commit` | • `odoo-core-source`<br>• `odoo-postgres`<br>• `context7` | • **`odoo-core-source`**: Verify stability and safety of overridden base methods.<br>• **`odoo-postgres`**: Inspect indexes, foreign keys, and query plans (`EXPLAIN`) to prevent N+1 queries.<br>• **`context7`**: Validate against modern best practices. | `docs/review/<feature>.md`<br>*(Strictly Read-Only on codebase)* |
| **5. Documentation & Manifest** | `documentation-engineer`<br>*(or `technical-writer`)* | `odoo-19` (`manifest`, `translations`), `api-documenter` | • `odoo-rpc`<br>• `chrome-devtools` | • **`odoo-rpc`**: Extract live menus, actions, and models for documentation.<br>• **`chrome-devtools`**: Capture final UI screenshots for `static/description/index.html`. | `__manifest__.py`, `README.md`, `static/description/index.html`, `docs/` |

---

## 3. Specialized MCP Operational Rules

### 3.1. Coordinated `playwright` + `chrome-devtools` Session (for `qa-expert`)
When verifying user interfaces (XML views, OWL 2 components, JS/SCSS), `qa-expert` must orchestrate both MCP servers:
1. **Interactive Navigation via `playwright`**:
   - Always query the Accessibility Tree (`browser_snapshot`) to navigate, trigger buttons, fill fields, and execute wizards without unnecessary visual token overhead.
2. **Surveillance & Auditing via `chrome-devtools`**:
   - Inspect Console messages via `list_console_messages`: Enforce **Zero Console Errors** (no `OwlError`, `UncaughtPromiseError`, `TypeError`, or missing asset failures).
   - Inspect Network RPC via `list_network_requests` filtering on `/web/dataset/call_kw/` to verify HTTP 200 and absence of server traceback envelopes.
   - Record screenshots to `docs/review/screenshots/<feature>_<step>.png`.

### 3.2. Safety Policies for `odoo-postgres` and `odoo-rpc`
- **`odoo-postgres` (Read-Only Inspection)**: Subagents may only execute `SELECT` or `EXPLAIN` queries to inspect table schemas, constraints, `ir_ui_view`, `ir_model_data`, and `ir_rule`. Direct `UPDATE`, `DELETE`, `DROP`, or `ALTER` SQL statements are **STRICTLY PROHIBITED** to preserve ORM registry consistency.
- **`odoo-rpc` & `scripts/run_test.py`**:
  - Quick validation calls (`search_read`, `fields_get`, isolated method invocations) should be executed directly via `odoo-rpc`.
  - Complex multi-step test scripts intended for reproducibility must be written to the **single designated script file `scripts/run_test.py`** and must include an explicit `cleanup()` teardown procedure.

### 3.3. Anti-Hallucination Policies with `odoo-core-source` & `context7`
- **Mandatory Pre-Read:** Before inheriting any model (`_inherit`) or extending any view (`inherit_id`) in Odoo 19, subagents **must inspect the base source code** inside `/opt/odoo19/odoo` and `/opt/odoo19/addons` using `odoo-core-source`.
- **Citation Requirement:** In `docs/analysis/<feature>.md`, explicitly cite the exact file path and line/node of the parent model or XML view being inherited. Never guess field names, method signatures, or view XML structures.
- When uncertain regarding Odoo 19 APIs or OWL 2 syntax, consult `context7` or `fetch-docs` before writing code.

---

## 4. Standard Workflow Pipelines

### Pipeline A: Feature Development & Module Enhancement

1. **Phase 1 — Deep Analysis & Specification (`business-analyst` / `architect-reviewer`):**
   - Use `odoo-core-source`, `odoo-postgres`, `odoo-rpc`, and `context7` to inspect current system architecture.
   - Produce `docs/analysis/<feature>.md` containing:
     - **Context & Core Tracing:** Exact core models/views inspected via MCP.
     - **Architecture & Data Model:** Exact model names, field types, `@api.depends` chains, and `xml_id` list.
     - **UI & XPath Blueprint:** Exact target `inherit_id` and verified `xpath` expressions.
     - **Acceptance Criteria (AC):** Testable functional and technical criteria.
   - **Exit Gate:** Present a clear architectural explanation and summary to the User. Obtain approval if requirements are ambiguous; proceed autonomously if full execution was requested.

2. **Phase 2 — TDD Red Phase (`qa-expert` / `test-automator`):**
   - Read `docs/analysis/<feature>.md` and load the `odoo-automated-tests` skill.
   - Author standard `TransactionCase` tests under `<module>/tests/test_<feature>.py` covering all Acceptance Criteria.
   - Execute the test suite and verify that tests **fail for the expected reason** (unimplemented feature, not syntax errors).
   - **Exit Gate:** Attest status `RED CONFIRMED`.

3. **Phase 3 — TDD Green Phase (`backend-developer` / `python-pro` / `frontend-developer`):**
   - Read `docs/analysis/<feature>.md` and the test suite under `<module>/tests/`.
   - Implement the feature using skill `odoo-19` with MCPs `odoo-core-source` and `context7`.
   - **Immediate Terminal Upgrade Gate:** After writing/editing module files, run the Odoo CLI upgrade check (`-d odoo19 -u <module> --stop-after-init`) to immediately catch and self-correct any XML `ParseError`, missing imports, or registry crashes before handing off to QA.
   - **STRICT PROHIBITION:** Never modify or delete existing test assertions in `<module>/tests/` simply to force a passing build.
   - **Exit Gate:** Module installs/upgrades cleanly with exit code `0` and is submitted for parallel verification.

4. **Phase 4 — Parallel Verification & Review:**
   - **QA Verification (`qa-expert` / `test-automator`):**
     - Run module tests and dependent test suites (`--test-enable`), ensuring logic test coverage **greater than 80%**.
     - Seed real test data and execute API scenario testing using the local GraphQL gateway module (`/opt/odoo19/dev/dn_graphql_gateway`): execute mutations and queries, asserting `0` `result.errors` and `0` `userErrors`. Verification is strictly considered **PASS/OK** only when GraphQL execution completes with **ZERO ERRORS**.
     - Verify database state via `odoo-rpc` / `odoo-postgres` or `scripts/run_test.py`.
     - **Mandatory UI Gate (Browser Subagent / Playwright):** For ANY change affecting `views/*.xml` or `static/src/**/*`, authenticate at `http://localhost:8019/web?db=odoo19`, perform end-to-end interactions, verify **Zero Console Errors**, and record screenshots to `docs/review/screenshots/`.
   - **Code Review (`code-reviewer` / `odoo-code-review`):**
     - Operates in **Read-Only** mode.
     - Inspect method overrides, security ACLs, and query efficiency against Odoo Core using `odoo-core-source` and `odoo-postgres`.
     - Output findings to `docs/review/<feature>.md` classified into 4 severity levels: `BLOCKER`, `MAJOR`, `MINOR`, `NIT`.
   - **Self-Correction Loop (Maximum 3 Cycles):**
     - If terminal upgrade fails, tests fail, console errors occur, or the review notes `BLOCKER` / `MAJOR` issues: automatically return to Phase 3 (`backend-developer`) for resolution, then re-execute Phase 4 without asking the user to debug manually.
     - If after **3 cycles** the solution has not achieved `PASS` + `APPROVED`, halt execution and report detailed blockers to the User.

5. **Phase 5 — Manifest & Documentation (`documentation-engineer`):**
   - **Activation Gate:** Triggers only when Phase 4 satisfies both conditions: `qa-expert` reports **PASS** and `code-reviewer` marks **APPROVED**.
   - Update `__manifest__.py` (version, depends, data, summary, description).
   - Update `static/description/index.html` (embedding screenshots from `docs/review/screenshots/`) and `README.md`.

---

### Pipeline B: Rapid Bug Fix Flow

1. **Reproduction (`qa-expert`):** Reproduce the bug using `odoo-rpc` / `playwright` and create a reproduction test in `<module>/tests/` -> Confirm test failure.
2. **Root Cause Analysis & Fix (`backend-developer` / `frontend-developer`):** Use `odoo-core-source` and `odoo-postgres` to identify root causes, explain the exact cause to the user, and apply fixes in source files without touching test definitions.
3. **Verification & Audit (`qa-expert` & `code-reviewer`):** Run module upgrade & tests, perform UI audit via `playwright` + `chrome-devtools` (for UI defects), and publish review to `docs/review/<bugfix>.md`.
4. **Manifest Patch (`documentation-engineer`):** Increment the patch version in `__manifest__.py` if business code was updated.

---

### Pipeline C: Functional Consulting & Deep Technical Q&A (No-Code Flow)

When the user asks a functional question, requests an explanation of Odoo 19 behavior, or explores architecture:
1. **Source & DB Grounding (`odoo-analyst` / Community Subagent):**
   - Search `/opt/odoo19/addons` via `odoo-core-source` to locate the exact models, compute methods, and workflows involved.
   - Query `odoo-postgres` or `odoo-rpc` if the question relates to existing database records, views, or installed modules.
2. **Synthesis & Deep Explanation:**
   - Explain the **business logic flow** step-by-step alongside the **technical implementation** (exact model names, method names, and trigger conditions).
   - Highlight Odoo 19 specific changes (e.g., changes from v16/v17 to v19) backed by `context7` / `odoo-core-source`.

---

## 5. Mandatory Technical Standards for Odoo 19

### 5.1. ORM, Python & Security (`odoo-19` Skill)
- **Creation Batching:** Implement `@api.model_create_multi` on all `create` methods.
- **Display Name:** Use `_compute_display_name(self)` instead of deprecated `name_get()`.
- **Command Syntax:** Use `from odoo.fields import Command` (`Command.create`, `Command.update`, `Command.link`, `Command.set`...) instead of deprecated magic tuples `(0, 0, ...)`, `(4, ...)`, `(6, 0, ...)`.
- **N+1 Query Prevention:** Never invoke `search()`, `browse()`, or access un-prefetched relational fields inside loops; use `_read_group`, `search_fetch()`, `mapped()`, or `filtered()`.
- **Raw SQL Protection:** Avoid raw SQL (`cr.execute`); when required for exceptional performance optimization, always wrap queries with `odoo.tools.SQL`.
- **Security & Multi-Company:** Every model must have ACL declared in `security/ir.model.access.csv` and multi-company record rules (`ir.rule` on `company_id`). Every `.sudo()` call must include an inline reason comment: `# sudo: <reason>`.

### 5.2. Views XML & OWL 2 Frontend
- **Odoo 19 View Tags:** ALWAYS use `<list>` instead of deprecated `<tree>`, and `<chatter/>` instead of legacy `<div class="oe_chatter">` blocks.
- **Direct XML Modifiers:** Follow Odoo 17–19 XML standards: Use direct Python expressions `invisible="..."`, `readonly="..."`, `required="..."` on `<field>` and `<button>`. **PROHIBITED:** Legacy `attrs="{...}"` or `states="..."`.
- **OWL 2 Component Architecture:** Start all JS files with `/** @odoo-module **/`. Manage component lifecycles exclusively through standard `@odoo/owl` hooks (`useService`, `useState`, `onWillStart`, `onMounted`, `onWillDestroy`) and `registry.category("...").add(...)`. Never use legacy `odoo.define()`.

### 5.3. Manifest Guidelines (`__manifest__.py`)
- Use clear inline section headers.
- `summary`: Exactly 1 concise sentence summarizing the module's core purpose.
- `description`: Comprehensive markdown overview with a `## Features` section.
- Enforce strict loading sequence in the `'data'` list:
  1. `security/ir.model.security.xml` (Groups, categories, record rules)
  2. `security/ir.model.access.csv` (Access Control Lists)
  3. `data/*.xml` (Sequences, cron jobs, seed records)
  4. `views/*.xml` (Form, List, Kanban, Search views & Actions)
  5. `wizard/*.xml` (TransientModel views & actions)
  6. `report/*.xml` (QWeb Reports & Paper formats)
  7. `views/menus.xml` (Menu hierarchies loaded last)

### 5.4. Versioning & Migration Standards
- **Format:** `19.0.<major>.<minor>.<patch>` (e.g., `19.0.1.0.0`).
  * `major`: Major architectural restructuring or breaking changes.
  * `minor`: New features, new models, or schema adjustments.
  * `patch`: Minor bug fixes or optimizations without schema modifications.
- **Migration Scripts:** When altering existing schemas (renaming models/fields, changing column types) and incrementing versions, provide migration scripts under `migrations/19.0.<major>.<minor>.<patch>/pre-migrate.py` or `post-migrate.py` (applying skill `odoo-19`).
- **Version Bump Prohibition:** Do NOT increment `__manifest__.py` versions if changes are limited solely to documentation (`docs/`, `README.md`) or test cases (`tests/`).

### 5.5. Workspace Hygiene
- External Python test scripts are restricted **strictly to `scripts/run_test.py`**. Do not create temporary ad-hoc scripts like `test_temp.py`, `debug.py`, or `check_rpc.py`.
- Before delivery, ensure no debugging artifacts remain in code: eliminate all `breakpoint()`, `pdb.set_trace()`, `print()`, and `console.log()` statements.

---

## 6. Shared Browser Session Configuration (CDP Port 9222)

To ensure that `qa-expert` synchronizes `@playwright/mcp` (DOM accessibility interaction) and `chrome-devtools-mcp` (console errors and screenshots) within the same browser instance, attach both servers to a unified Chrome DevTools Protocol port (`9222`) configured in `.agents/mcp.json`.

---

## 7. Modular Rules Reference (`.agents/rules/`)

In accordance with Antigravity rules standards, detailed constraints and specialized playbooks are modularized under `.agents/rules/`:
- **`odoo-engineering-verification.md`** (`trigger: always_on`): Strict Odoo 17-19 syntax (XML `<list>`, `<chatter/>`, direct modifiers, ORM anti-N+1 batching), and closed-loop verification (CLI upgrade + browser UI checks).
- **`workspace-code-environment.md`** (`trigger: always_on`): Direct workspace file editing, prohibition of code fabrication/hallucination, mandatory runtime `/opt/venv312/bin/python3.12` and configuration `/opt/odoo19.conf`.
- **`odoo-ui-testing.md`** (`trigger: glob` on XML views & static assets): Detailed 5-step Playwright + Chrome DevTools UI testing playbook and Odoo 19 OWL 2 CSS selectors quick reference.

