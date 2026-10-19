---
trigger: glob
globs: "**/views/*.xml, **/static/src/**/*"
description: "Odoo 19 UI Testing Workflow with Playwright and Chrome DevTools, plus OWL 2 CSS selectors reference."
---

# ODOO 19 UI TESTING PLAYBOOK & CSS SELECTORS

## 1. Browser Automation Architecture (Antigravity Browser Subagent & Playwright/CDP)
When testing XML views, OWL components, or web assets, orchestrate UI verification via:
- **Antigravity Browser Subagent**: Driven via Chrome to authenticate (`http://localhost:8019/web?db=odoo19`), execute DOM interactions, audit console errors, and capture screenshots automatically during UI verification tasks.
- **Playwright MCP (`@playwright/mcp`) & Chrome DevTools MCP (`chrome-devtools-mcp`)**: Alternately connects via CDP port (`9222`) to execute DOM actions (`browser_snapshot`) and verify RPC network calls / console logs.

---

## 2. 5-Step UI Verification Procedure
1. **Step 1: Login & Session Initialization:** Navigate to `/web/login?db=odoo19`, snapshot inputs, submit credentials, wait for `.o_navbar`, and audit console messages via `list_console_messages`.
2. **Step 2: Direct Navigation:** Navigate directly to the action view URL (e.g., `/odoo/action-<id>/new`) or click `"New"` (`.o_list_button_add`), followed by `browser_snapshot`.
3. **Step 3: Widget Interactions:**
   - Standard inputs (`Char`, `Integer`): Type and send `Tab` key to trigger `@api.onchange`.
   - `Many2one` dropdowns: Click input, search, wait for `.o-autocomplete--dropdown-menu`, click first item.
   - `One2many` line items: Click `"Add a line"`, snapshot the inline row, and fill values.
   - Dynamic visibility: Confirm `invisible` / `readonly` states reflect onchange modifications.
4. **Step 4: Save & Quality Audit:**
   - Click Save (`.o_form_button_save`) or header action buttons.
   - **Quality Gate:** Zero Console Errors (`list_console_messages`). Verify RPC HTTP 200 without server error blocks (`list_network_requests`).
   - Capture screenshots: `docs/review/screenshots/<feature>_01_form_filled.png` and `docs/review/screenshots/<feature>_02_after_action.png`.
5. **Step 5: Backend Verification & Cleanup:** Query `search_read` via `odoo-rpc` to verify stored fields, followed by `unlink` to clean test records.

---

## 3. Odoo 19 (OWL 2) Standard CSS Selectors Quick Reference

| UI Component | Standard CSS Selector | State / Identification Notes |
| :--- | :--- | :--- |
| **Main Form View** | `.o_form_view` | Has class `.o_form_editable` (edit mode) or `.o_form_saved` (saved) |
| **Action Buttons: New / Save / Discard** | `.o_form_button_create`, `.o_form_button_save`, `.o_form_button_cancel` | Save button contains upload cloud icon (`fa-cloud-upload`) |
| **Statusbar** | `.o_statusbar_status button.o_arrow_button_current` | Shows active stage name (e.g., `Draft`, `Posted`) |
| **Header Action Buttons** | `.o_statusbar_buttons button[name="<method_name>"]` | Matches the `name` attribute in XML `<button>` |
| **Field Widget** | `.o_field_widget[name="<field_name>"]` | Has `.o_field_invalid` class if missing required data |
| **Error Dialog / Traceback** | `.o_error_dialog`, `.modal-content .o_error_detail` | Displayed upon `ValidationError`, `UserError`, or `AccessError` |
| **Toast Notifications** | `.o_notification_manager .o_notification` | Contains feedback messages from `display_notification` |
