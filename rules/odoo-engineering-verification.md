---
trigger: always_on
description: "Strict Odoo 17-19 engineering standards, modern ORM/XML syntax rules, and mandatory closed-loop verification workflow."
---

# ODOO 17-19 STRICT ENGINEERING & VERIFICATION RULES

## 0. ENVIRONMENT CONFIGURATION (CENTRALIZED VIA `.agents/.env`)
All environment parameters are dynamically loaded from `/opt/odoo19/.agents/.env`:
- **Config File:** `/opt/odoo19/.agents/.env`
- **Target Odoo Version:** 19.0 (Strict adherence to Odoo 17/18/19+ modern standards)
- **Odoo CLI Command:** `$ODOO_PYTHON $ODOO_BIN -c $ODOO_CONF` (Read from `.agents/.env`)
- **Database Name:** `$ODOO_DB` (Configured in `.agents/.env`)
- **Web Server URL:** `$ODOO_URL` (Configured in `.agents/.env`)
- **Test Credentials:** `$ODOO_ADMIN_USER` / `$ODOO_ADMIN_PASSWORD` (Configured in `.agents/.env`)

---

## 1. MANDATORY WORKFLOW: PLAN -> EXECUTE -> VERIFY
You are strictly forbidden from jumping straight into multi-file code generation without planning and grounding. Follow this exact 4-phase lifecycle for every task:

### Phase 1: Context Grounding & Implementation Plan (DO NOT SKIP)
1. **Read Before Write:** Before modifying models, inheriting views (`xpath`), or patching OWL components, you MUST use file-reading or search tools (`grep`/`read_file`) to inspect existing models, exact field names, and target `xml_id`s. **NEVER guess or hallucinate field names or External IDs.**
2. **Blueprint First:** For any new module or feature involving >2 files, first output a concise **Implementation Plan** detailing:
   - Exact file tree to be created/modified.
   - Model names (`_name`, `_inherit`) and exact field definitions.
   - XML IDs (`id="..."`) and security groups.
   - Wait for confirmation if architectural requirements are ambiguous.

### Phase 2: Code Execution (Strict Odoo 17-19 Syntax)
Adhere 100% to modern Odoo standards. Legacy Odoo 14/15/16 syntax is strictly prohibited:

#### A. XML Views
- **List Views:** Depending on target version:
  - For **Odoo 18 / 19**: ALWAYS use `<list>` instead of `<tree>`.
  - For **Odoo 17**: `<tree>` is acceptable, but NEVER mix `<tree>` and `<list>` inconsistently within the same module.
- **Inline Modifiers:** NEVER use `attrs="{'invisible': ..., 'readonly': ..., 'required': ...}"` or `states="..."`. ALWAYS use direct Python expression attributes:
  - Correct: `invisible="state != 'draft'"`
  - Correct: `readonly="state == 'done'"`
  - Correct: `required="is_company == True"`
- **View Inheritance:** Before writing any `<xpath expr="..." position="...">`, you MUST read the parent XML view in the source code to verify the target node exists.
- **Chatter:** Use `<chatter/>` tag (Odoo 18/19) instead of the legacy `<div class="oe_chatter">` block when targeting v18/v19.

#### B. Python & ORM
- **Decorators & Methods:**
  - ALWAYS use `@api.model_create_multi` when overriding `create(self, vals_list)`.
  - Use `_compute_display_name(self)` instead of deprecated `name_get()`.
  - Always declare explicit `store=True` or `store=False` with accurate `@api.depends(...)` paths.
- **Performance (Anti-N+1):**
  - NEVER execute `search()`, `browse()`, or SQL queries inside a `for record in self:` loop.
  - Batch fetch data before loops using `_read_group()`, `search_fetch()`, or `mapped()` / `filtered()`.
- **Security & Manifest:**
  - Every new non-abstract model (`models.Model`) MUST have a corresponding entry in `security/ir.model.access.csv`.
  - Every new `.py` file MUST be imported in `__init__.py`.
  - Every new `.xml`, `.csv`, or asset file MUST be declared in `__manifest__.py` in the correct load order (`security` -> `data` -> `views` -> `menus`).

#### C. Frontend (OWL 2 & JavaScript)
- **ES Modules Only:** ALWAYS start JS files with `/** @odoo-module **/`. NEVER use legacy `odoo.define()`.
- **OWL Standards:** Use standard `@odoo/owl` hooks (`Component`, `useState`, `onWillStart`, `onMounted`, `useRef`) and register components/fields via `registry.category("...").add(...)`.
- **Services:** Use `useService("orm")`, `useService("action")`, `useService("notification")` instead of legacy RPC calls.

---

## 2. CLOSED-LOOP VERIFICATION (DEFINITION OF DONE)
**CRITICAL RULE:** Generating code is only 50% of the task. You are **FORBIDDEN** from marking a task as completed until you have executed the verification loop below.

### Step 1: Terminal Init & Test Check (Mandatory after ANY Python/XML change)
Immediately after writing or editing module files, use the Terminal tool to run (variables loaded from `/opt/odoo19/.agents/.env`):
```bash
set -a && source /opt/odoo19/.agents/.env && set +a
$ODOO_PYTHON $ODOO_BIN -c $ODOO_CONF -d $ODOO_DB -u <module_name> --stop-after-init --log-level=warn
```

*(If unit tests exist or were requested, append `--test-enable`)*

- **Self-Correction Rule:** Carefully inspect the terminal output. If you see ANY `Traceback`, `ParseError`, `ValueError`, `KeyError`, `ValidationError`, or `WARNING/ERROR` related to the module:
  1. Do NOT ask the user what to do.
  2. Analyze the traceback, locate the offending line in `.py` or `.xml`, fix it immediately, and re-run the command until exit code is `0` with zero errors.

### Step 2: Browser UI & OWL Inspection (Mandatory for ANY View/JS/UI task)
Once Step 1 passes cleanly:
1. Ensure the Odoo server is running in the background (or start it if stopped).
2. Activate the **Browser Agent** (Antigravity Browser Subagent or Playwright) and navigate to `$ODOO_URL/web?db=$ODOO_DB` (values from `.agents/.env`).
3. Log in (if prompted) using the Test Credentials above.
4. Navigate to the newly created/modified Menu, List View, and Form View.
5. **Visual & Console Check:**
   - Take a screenshot of the rendered view to verify layout integrity.
   - Check the browser console/DOM for any OWL `Uncaught Promise`, `OwlError`, or missing widget errors.
   - Click at least one button or create a sample record to verify the form saves without RPC errors.
6. If any UI error or broken layout appears, fix the code, reload/upgrade, and re-verify in the Browser before delivering the final answer.
