---
trigger: always_on
description: "Mandates direct workspace code modification, forbids fabricated or hallucinated code, and enforces using /opt/venv312/bin/python3.12 and /opt/odoo19.conf."
---

# WORKSPACE CODE INTEGRITY & ENVIRONMENT EXECUTION RULES

## 1. DIRECT WORKSPACE CODE EXECUTION (NO PSEUDO-CODE)
- **Physical Workspace Writing:** All code modifications, new Odoo modules, tests, views, and configurations MUST be written directly into actual files within the workspace (`/opt/odoo19`).
- **Forbidden Actions:**
  - NEVER output code solely in conversation text while pretending it has been applied to the codebase.
  - NEVER write project files outside the workspace root (`/opt/odoo19`).
  - NEVER skip creating or modifying the physical file before claiming a task or step is done.

---

## 2. STRICT ZERO-HALLUCINATION POLICY (NO FABRICATED CODE)
- **Evidence-Before-Writing Law:** Before declaring, inheriting, or modifying any Odoo model, field, method, or XML view, you MUST inspect the actual source code within `/opt/odoo19/addons`, `/opt/odoo19/odoo`, or `/opt/odoo19/dev`.
- **Forbidden Actions:**
  - NEVER invent or guess model names (e.g. guessing `sale.order.line.tax` instead of inspecting `account.tax` or `sale.order.line`).
  - NEVER guess field names or relational attributes (`comodel_name`, `relation`, `column1`, `column2`).
  - NEVER invent XPath expressions without reading the exact parent view definition and verifying the target tag or attribute exists.
  - NEVER invent super method signatures or return types; always verify the base method implementation in the workspace first.

---

## 3. STRICT PYTHON RUNTIME INTERPRETER
- **Mandatory Python Binary:** ALWAYS invoke Python via the dedicated virtual environment interpreter:
  ```bash
  /opt/venv312/bin/python3.12
  ```
- **Forbidden Actions:**
  - NEVER use unaliased `python` or generic `python3` commands when executing Odoo scripts, runners, or tests.
  - All script execution (e.g., `scripts/run_test.py`, test runners, migration scripts) must explicitly use `/opt/venv312/bin/python3.12`.

---

## 4. STRICT ODOO CONFIGURATION FILE
- **Mandatory Configuration Flag:** ALWAYS provide the explicit configuration file `/opt/odoo19.conf` in all Odoo CLI executions:
  ```bash
  /opt/venv312/bin/python3.12 /opt/odoo19/odoo-bin -c /opt/odoo19.conf -d odoo19 ...
  ```
- **Forbidden Actions:**
  - NEVER run `odoo-bin` without `-c /opt/odoo19.conf`.
  - NEVER invent or assume non-existent config files (e.g., `odoo.conf`, `debian/odoo.conf`).
