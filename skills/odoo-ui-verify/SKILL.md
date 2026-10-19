---
name: odoo-ui-verify
description: "End-to-end UI and OWL 2 verification playbook for Odoo 19 using synchronized Playwright and Chrome DevTools over CDP (port 9222). Covers login, Form view interaction, widget handling (Many2one, One2many), action execution, zero-console-error gating, network call_kw inspection, and screenshot evidence."
---

# Playbook: Odoo 19 UI Testing Workflow (`playwright` + `chrome-devtools`)

**Target Subagents:** `qa-expert`, `test-automator`  
**Objective:** Automatically authenticate to Odoo 19, interact with Form/List Views, verify Zero Console Errors (OWL 2 / JS), validate RPC responses, and record screenshot evidence into `docs/review/screenshots/`.

---

## 1. Tool Routing Principles

1. **Use `playwright` for interactive DOM actions (Action):**
   - Always invoke `browser_snapshot` to inspect the Accessibility tree (YAML) instead of taking full screenshots repeatedly, minimizing token consumption.
   - Use `browser_click`, `browser_type`, `browser_select_option`, `browser_press_key`, and `browser_wait_for` based on element `ref` obtained from `browser_snapshot`.
2. **Use `chrome-devtools` for inspection & evidence (Inspection & Evidence):**
   - Use `list_console_messages` to capture JS errors, OWL Lifecycle faults, and missing asset bundle issues.
   - Use `list_network_requests` / `get_network_request` to inspect JSON-RPC payloads (`/web/dataset/call_kw/...`) when UI actions fail to respond.
   - Use `take_screenshot` to export visual evidence into `docs/review/screenshots/<feature>_<step>.png`.

---

## 2. 5-Step Execution Workflow

### Step 1: Authentication & Session Initialization (`playwright` / Browser Subagent)
1. Navigate to `http://localhost:8019/web/login?db=odoo19`.
2. Get field elements:
   - Type Email/Username (`input[name="login"]`) and Password (`input[name="password"]`).
   - Click `"Log in"` (`button[type="submit"]`).
3. Wait until redirected to `/odoo` and the navigation bar `.o_navbar` is rendered.
4. Verify console messages immediately after WebClient loads to confirm `web.assets_web.min.js` compiled cleanly without SCSS/JS syntax errors.

### Step 2: Direct Navigation to Target Form View
*Tip for Odoo 19:* Avoid navigating through nested menus unless menu routing itself is under test.
1. (Optional) Query `ir.actions.act_window` via `search_read` to retrieve the `id` or `path` for the action.
2. Navigate directly:
   - Via clean Odoo 19 URL: `http://localhost:8019/odoo/action-<action_id>/new` (opens new record Form directly) or click `"New"` (`.o_list_button_add`) from List View.
   - Invoke `browser_snapshot` to capture all fields and controls on `.o_form_view`.

### Step 3: Interacting with Odoo 19 Form View Widgets (`playwright`)
Based on `browser_snapshot` results, test each field type defined in `docs/analysis/<feature>.md`:

1. **Standard Fields (`Char`, `Integer`, `Float`, `Text`):**
   - Use `browser_type` on the input element inside `.o_field_widget[name="<field_name>"]`.
   - Press `Tab` (`browser_press_key`) to trigger `@api.onchange` events.
2. **Relational `Many2one` Fields (`.o_field_many2one`):**
   - Click the input inside `.o_field_many2one`.
   - Type the search query using `browser_type`, wait for `.o-autocomplete--dropdown-menu`, then click the first result (`.ui-menu-item`).
3. **One2many Line Items (`.o_field_x2many_list`):**
   - Click `"Add a line"` (`a[role="button"]` inside `.o_field_x2many_list_row_add`).
   - Call `browser_snapshot` to obtain `ref`s for the inline editable row (or popup dialog) and fill values.
4. **Dynamic Visibility & State (`invisible`, `readonly`, `required`):**
   - After altering condition fields, call `browser_snapshot` to verify that target fields are toggled or disabled (`disabled`/`readonly`) as declared in XML views.

### Step 4: Record Save, Action Execution & Console/Network Audit (`chrome-devtools`)
1. **[playwright]** Click Save (`.o_form_button_save`) or trigger the header action button (e.g., `"Confirm"`, `"Post"`).
2. **[chrome-devtools]** Enforce the Quality Gate:
   - **Console Inspection:** Call `list_console_messages`. If any log contains `UncaughtPromiseError`, `OwlError`, `RPC_ERROR`, `TypeError`, or `KeyError`:
     - Call `get_console_message` to extract the full traceback.
     - Fail the test immediately.
   - **Network RPC Inspection:** Call `list_network_requests` filtered on `/web/dataset/call_kw/`. Verify HTTP 200 and ensure the JSON response body contains no `"error": {"code": 200, "message": "Odoo Server Error"}` payload.
   - **Visual Evidence:** Call `take_screenshot` and save according to standard paths:
     - `docs/review/screenshots/<feature>_01_form_filled.png` (Values input & onchange evaluated).
     - `docs/review/screenshots/<feature>_02_after_action.png` (Post-action execution & statusbar updated).

### Step 5: Backend Reconciliation & State Teardown (`odoo-rpc`)
1. **[odoo-rpc]** Invoke `search_read` on the model to verify computed stored fields (`store=True`) persisted accurately in PostgreSQL.
2. **[odoo-rpc]** Call `unlink` to clean up test records, preserving test database hygiene.

---

## 3. Odoo 19 (OWL 2) Standard CSS Selectors Quick Reference

| UI Component | Standard CSS Selector | State / Identification Notes |
| :--- | :--- | :--- |
| **Main Form View** | `.o_form_view` | `.o_form_editable` (editing) or `.o_form_saved` (saved) |
| **Action Buttons: New / Save / Discard** | `.o_form_button_create`, `.o_form_button_save`, `.o_form_button_cancel` | Save button displays cloud upload icon (`fa-cloud-upload`) |
| **Statusbar** | `.o_statusbar_status button.o_arrow_button_current` | Displays active record state (e.g., `Draft`, `Posted`) |
| **Header Action Buttons** | `.o_statusbar_buttons button[name="<method_name>"]` | Matches the `name` attribute declared on XML `<button>` |
| **Field Widget** | `.o_field_widget[name="<field_name>"]` | Contains `.o_field_invalid` on missing required value |
| **Error Dialog / Traceback** | `.o_error_dialog`, `.modal-content .o_error_detail` | Displayed upon `ValidationError`, `UserError`, or `AccessError` |
| **Toast Notifications** | `.o_notification_manager .o_notification` | Contains system alerts from `display_notification` |
