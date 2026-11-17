---
name: odoo-19-api-highlights
description: Version-distinguishing API patterns for Odoo 19. Read this when the target version is 19.0 so the reviewer/tracer applies the right rules.
---

# Odoo 19 API Highlights

Use this file as the version-specific ruleset when the resolved Odoo version is `19.0`. It supplements — not replaces — the general review checklist. Everything from 18 applies unless noted below.

## Models

- **`_name` fallback** — when `_name` is missing, Odoo 19 derives it from the CamelCase class name (each capital letter → `.` separator) and logs the warning `Class ... has no _name, please make it explicit`. Keep `_name` explicit on new models:
  - `ResPartner` → `res.partner`
  - `SaleOrder` → `sale.order`
  - `MyModel` → `my.model`
- A **string** `_inherit` without `_name` still means `_name = _inherit`, silently. A **list** `_inherit` does not: `class Partner` with `_inherit = ['res.partner']` and no `_name` becomes a new model `partner` (Odoo 18 used `_inherit[0]` for a one-item list). Extensions with a list `_inherit` need `_name` or a class name that maps to the model.
- **`_sql_constraints` is ignored** — Odoo 19 logs `Model attribute '_sql_constraints' is no longer supported` and creates nothing. Declare table objects as class attributes whose name starts with `_`: `models.Constraint('UNIQUE(code)', 'message')`, `models.Index('(col_a, col_b)')`, `models.UniqueIndex('(code) WHERE active', 'message')`. The SQL name is `<table>_<attribute name without the leading _>`.
- **`read_group()` is deprecated** (since 19.0) — use `_read_group()` in backend code, or `formatted_read_group()` when the formatted result is needed.
- **`self._cr` / `self._uid` / `self._context` are deprecated** (since 19.0) — use `self.env.cr` / `self.env.uid` / `self.env.context`.
- Reference: `references/odoo-19-model-guide.md`.

## Views

- Same as 18: `<list>` tag, direct-expression attrs. Reference: `references/odoo-19-view-guide.md`.
- **`<group expand= string=>` removed from search views** — the RelaxNG schema (`search_view.rng` & `common.rng`) no longer allows `expand` or `string` attributes on `<group>` inside a `<search>`. Using them raises `ParseError: Invalid attribute expand/string for element group` at module install/upgrade.
  - ❌ `<group expand="0" string="Group By">` — **INVALID in 19, causes ParseError**
  - ❌ `<group string="Group By">` — **INVALID in 19, causes ParseError**
  - ✅ `<group name="group_by">` or `<group>` — correct form; the label is automatic or not needed on group container in search view

## Fields

- Same as 18: `aggregator=` for aggregation. Reference: `references/odoo-19-field-guide.md`.

## Decorators

- Same as 18: `@api.ondelete`, `@api.model_create_multi`.
- **`@api.returns` no longer exists** — `odoo.api` does not export it in 19, so `@api.returns(...)` fails at import.
- **`@api.private`** — marks a public method as not callable over RPC (also available in 18). Names starting with `_` are already refused over RPC; use the decorator for public or ORM method names.
- Reference: `references/odoo-19-decorator-guide.md`.

## Databases and tests

- New databases are created **without** demo data unless `--with-demo` is passed (Odoo 18 loads demo data by default). Tests must create their own records instead of relying on demo XML IDs or the `demo` / `portal` users.

## Security & Access Groups

- **`res.groups` schema changes in 19.0**:
  - `category_id` has been removed from `res.groups`. It is replaced by `privilege_id` (pointing to `res.groups.privilege`). A privilege in turn points to `category_id` (`ir.module.category`).
  - The `users` relation field on `res.groups` is named `user_ids` (writing to `users` raises `ValueError: Invalid field 'users' in 'res.groups'`).
  - Defining custom groups in XML:
    ```xml
    <!-- 1. Privilege -->
    <record id="privilege_custom_feature" model="res.groups.privilege">
        <field name="name">Feature Name</field>
        <field name="category_id" ref="base.module_category_custom"/>
    </record>

    <!-- 2. Group -->
    <record id="group_custom_feature" model="res.groups">
        <field name="name">Can edit feature</field>
        <field name="privilege_id" ref="privilege_custom_feature"/>
        <field name="user_ids" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
    </record>
    ```

## Accounting & Invoicing Synchronization

- **`account.move.line` Currency Rate & Payment Term Rebalancing**:
  - In Odoo 19, `account.move.line._sync_invoice()` automatically recalculates `line.balance = line.company_currency_id.round(line.amount_currency / line.currency_rate)` when `currency_rate` changes.
  - For `display_type == 'payment_term'`, recalculating balance directly via naive division causes off-by-cent rounding discrepancies with tax-rounded base lines (especially on non-decimal company currencies or low unit currencies like VND).
  - Solution: In custom rate modules or rate hooks, protect `balance` on `payment_term` lines during `_sync_invoice` and ensure the invoice payment term lines balance the entry in `_sync_dynamic_lines`.

## Quick review checks (v19-specific)

- ❌ `_sql_constraints = [...]` — ignored in 19; use `models.Constraint` / `models.Index` / `models.UniqueIndex`.
- ❌ `read_group(...)` in new code — use `_read_group(...)` or `formatted_read_group(...)`.
- ❌ `@api.returns(...)` — removed in 19.
- ❌ `self._cr` / `self._uid` / `self._context` — use `self.env.cr` / `self.env.uid` / `self.env.context`.
- ❌ New model without `_name` — works through the CamelCase fallback but logs a warning; set `_name`.
- ❌ List `_inherit` without `_name` on a class whose name does not map to the inherited model — creates a new model instead of extending it.
- ❌ `<group expand="0" string="Group By">` or `<group string="...">` inside `<search>` — **causes ParseError at install**; use `<group name="group_by">` or `<group>` instead.
- ✅ `@api.private` on a public method that must not be RPC-callable.
- All 18 rules still apply (`<list>`, direct-expression attrs, `aggregator=`, `@api.ondelete`, `@api.model_create_multi`, `check_access` / `has_access` / `_filtered_access`).
