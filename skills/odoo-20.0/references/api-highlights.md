---
name: odoo-20-api-highlights
description: Version-distinguishing API patterns for Odoo 20. Read this when the target version is 20.0 so the reviewer/tracer applies the right rules.
---

# Odoo 20 API Highlights

Use this file as the version-specific ruleset when the resolved Odoo version is `20.0`. It supplements — not replaces — the general review checklist. Everything from 19 applies unless noted below.

## System Requirements

- **Python**: Requires Python 3.12, 3.13, or 3.14 (`MIN_PY_VERSION = (3, 12)`).
- **PostgreSQL**: Requires PostgreSQL 16+ (`MIN_PG_VERSION = 16`).

## Security & Access Control (`ir.access`)

- **`ir.model.access` is completely replaced by `ir.access`**:
  - The security definition file is now `security/ir.access.csv` (never `ir.model.access.csv`).
  - CSV columns: `id,name,model_id,group_id/id,operation,domain`.
  - `model_id`: Model technical name directly, e.g. `sale.order` (NOT `model_sale_order`).
  - `group_id/id`: Group XML ID (e.g. `sales_team.group_sale_salesman`). If empty, the record is a **global restriction**.
  - `operation`: Combination of letters from `crud` (`r`, `ru`, `cru`, `crud`, `c`, `d`, etc.).
  - `domain`: Optional domain expression (replaces `ir.rule` and `domain_force`).
- **Unified Access Kind**:
  - Record with `group_id`: **Permission** (combined with `OR` across all user groups).
  - Record without `group_id`: **Restriction** (combined with `AND` across all global restrictions).
- **New `'access'` Domain Operator**:
  - `('rel_field', 'access', 'operation')` delegates access rights checks to parent records (e.g. `[('order_id', 'access', 'read')]`).
- **Security Method Changes**:
  - `check_field_access(field, operation)` replaces deprecated `_check_field_access()`.
  - `Model._access_domain(operation)` replaces deprecated `_check_access(operation)`.
  - `self.env.invalidate_access_cache()` replaces deprecated `clear_access_cache()`.
- Reference: `references/odoo-20-security-guide.md`.

## ORM & Models

- **`Model._table_query` is removed**:
  - Replaced by `@property def _table_sql(self) -> SQL:`. Custom SQL view models must implement `_table_sql` returning an `SQL` object instead of setting `_table_query`.
- **`BinaryValue` & `load='web'`**:
  - Binary field values are wrapped in `BinaryValue` (with `.filename`, `.content`, `.size`, `.mimetype`).
  - Parameter `bin_size` is completely removed from ORM. Use `load='web'` in `read()` / `search_read()` to return lightweight file metadata (`size`, `filename`).
  - Standard RPC format for binary fields returns `{'filename': ..., 'content': ..., 'size': ...}`.
- **`web_unlink`**:
  - New web client deletion method `def web_unlink(self)` that isolates foreign key/RESTRICT violations per record and raises `UnlinkBlockedError` with specific blocking details.
- **`exists()` blocked over RPC**:
  - `Model.exists()` is decorated with `@api.private` and is no longer callable externally over RPC.
- **`models.CachedModel`**:
  - New base class for models that cache stable records in memory (`ResCountry`, `ResLang`, `ResCompany`, `ResCurrency`, `Website`).
  - Uses `@api.ormcache(cache='stable')` with `_cached_data_fields` and `_cached_data_domain`.
  - Provides `get_all()` returning all cached instances.
- **`_rec_names_search`**:
  - Must be a **tuple** of field names, e.g. `_rec_names_search = ('name',)` (a list `['name']` is deprecated).
- **`compute_sql`**:
  - New field parameter `compute_sql='_compute_sql_xxx'` or callable `(model, table: TableSQL) -> SQL`.
  - Allows computed fields to be directly queried, filtered, and aggregated in SQL without being stored in the database.
  - Requires `compute` and an explicit `compute_sudo` parameter.
- **`init_storage`**:
  - Field parameter `init_storage='_init_storage_xxx'` on field definition replaces deprecated `_init_column(column_name)`.
- **`_table_has_rows`**: Removed / deprecated.
- **Recordset operations**:
  - `concat()` and `union()`: Call on an empty recordset with a single iterable, e.g. `self.env['model'].concat([r1, r2])`.
- **Cache & Transaction**:
  - `self.env.transaction.invalidate_ormcache(...)` replaces `registry.clear_cache()`.
  - `self.env.transaction.clear()` or `self.env.transaction.reset()` replaces `self.env.clear()`.
  - Import `ormcache` from `odoo.api`: `from odoo.api import ormcache` (importing from `odoo.tools.cache` is deprecated).
- **Domain expressions**:
  - AST-based `Domain` class (`from odoo.fields import Domain` or `from odoo.orm.domains import Domain`).
  - Supports `&`, `|`, `~`, `Domain.AND(...)`, `Domain.OR(...)`, `Domain.TRUE`, `Domain.FALSE`.
  - Relational operators: `'any'`, `'not any'`, `'any!'`, `'not any!'`, and `'access'`.
  - Boolean comparisons in domains must compare booleans to booleans: `('active', '=', True)`, not `('active', '=', 1)`.
  - Native dynamic dates: `'now'`, `'today'`, `'+1d'`, `'=1d'` supported in domains.
- **SQL Tools**:
  - `escape_like_value()` replaces deprecated `escape_psql()`.
- Reference: `references/odoo-20-model-guide.md` and `references/odoo-20-field-guide.md`.

## Frontend (OWL 3)

- **Props Declaration (`useProps`)**:
  - Static `props = {...}` and `defaultProps` are ignored/deprecated.
  - Declare props via `props = useProps({ ... })` using type validators from `t` in `@odoo/owl` (`t.string()`, `t.number()`, `t.boolean()`, `t.object()`, `t.array()`, `t.function()`, `t.any()`, with `.optional(default)`).
- **Reactivity (Proxy & Signals)**:
  - `useState` and `reactive` are replaced by `proxy(...)` from `@odoo/owl`.
  - Signals: `signal(initialValue)`, `signalRef()`, `signalArray()`, `signalObject()`, `signalMap()`, `signalSet()`, `computed(() => ...)`.
  - Signal values are read by calling the signal: `this.mySignal()`.
  - DOM Refs: `root = signal.ref()`, bound via `t-ref="this.root"`, accessed via `this.root()`.
- **Plugins Replace Services**:
  - In components, `useService('xxx')` is replaced by `usePlugin(PluginClass)` declared as class fields:
    - `orm = usePlugin(ORM);`
    - `action = usePlugin(ActionPlugin);`
    - `notification = usePlugin(NotificationPlugin);`
    - `dialog = usePlugin(DialogPlugin);`
- **Template Directives & `this.` Syntax**:
  - In QWeb templates, all component variables, props, and methods MUST use `this.` prefix (e.g. `this.props.x`, `this.state.y`, `this.handleClick`).
  - `<t t-call-slot="..."/>` replaces `<t t-slot="..."/>`.
  - `t-out` is mandatory; `t-esc` is removed/deprecated.
- **JavaScript Testing**:
  - Uses `@odoo/hoot` test framework: `import { expect, test } from "@odoo/hoot";`.
  - Test helpers: `@web/../tests/web_test_helpers` (`defineModels`, `defineActions`, `mountWithCleanup`, `contains`, `onRpc`).
- Reference: `references/odoo-20-owl-guide.md` and `references/odoo-20-testing-guide.md`.

## Views & Data Files

- **Search Date Filters**:
  - Attributes `start_month`, `end_month`, `start_year`, `end_year` are removed from `<filter name="..." date="..."/>`.
- **Parametric `t-call`**:
  - Direct attributes on `t-call`: `<t t-call="report.external_layout" doc="o"/>` or `variable.f="literal"` instead of child `<t t-set="doc" t-value="o"/>`.
- **XML Binary Fields**:
  - `<field name="datas" type="bytes" file="..."/>` replaces deprecated `type="base64"`.
- Reference: `references/odoo-20-view-guide.md` and `references/odoo-20-data-guide.md`.

## Controllers & External API

- **External API & Deprecation**:
  - The `db` service has been **completely removed** from `/xmlrpc`, `/xmlrpc/2`, and `/jsonrpc` (`ValueError: Invalid service name: db`).
  - The `common` and `object` services remain operational for backwards compatibility, but are officially deprecated in Odoo 19/20 and scheduled for permanent removal in Odoo 22.
  - The official modern external API is **/json/2** (`addons/rpc/controllers/json2.py`), routed at `POST /json/2/<model>/<method>`.
- **JSON-RPC Route**:
  - `@http.route(..., type='jsonrpc')` must be used (`type='json'` is a deprecated alias).
- **GeoIP**:
  - Object-based GeoIP API must be used (dictionary GeoIP API is deprecated).
- Reference: `references/odoo-20-controller-guide.md`.

## Reports & Printing

- **Paper Muncher Engine**:
  - New internal in-house report engine `base_report_paper_muncher` runs alongside `base_report_wkhtmltox` (wkhtmltopdf).
- **Removal of Report Watermark / Background Image**:
  - `res.company` report background image and watermark options have been removed without replacement. Custom report designs must rely on CSS/QWeb styling.

## Mail & UI Icons

- **Mail Tracking Values**:
  - `mail.tracking.value` model has been removed. Value tracking is handled via `mail.track.mixin` and generated directly into `mail.message` with `message_type='tracking'`.
- **UI Icons**:
  - Standard Font Awesome (`fa fa-`) has been replaced by Odoo UI Icons (`oi oi-...`) in the web client.

## Quick review checks (v20-specific)

- ❌ `Model._table_query` — removed in 20.0; use `@property def _table_sql(self) -> SQL:`.
- ❌ Calling `exists()` over RPC — decorated with `@api.private`.
- ❌ Passing `bin_size` to `read()` or context — removed; use `load='web'`.
- ❌ Calling `/xmlrpc/2/db` or `/jsonrpc` with service `'db'` — removed.
- ❌ `security/ir.model.access.csv` — must be `security/ir.access.csv`.
- ❌ `<record id="..." model="ir.rule">` in new code — declare in `security/ir.access.csv`.
- ❌ `_rec_names_search = ['name']` (list) — must be a tuple: `_rec_names_search = ('name',)`.
- ❌ `_check_field_access()` — use `check_field_access()`.
- ❌ `_check_access()` — use `Model._access_domain(operation)`.
- ❌ `clear_access_cache()` — use `invalidate_access_cache()`.
- ❌ `registry.clear_cache()` — use `self.env.transaction.invalidate_ormcache()`.
- ❌ `self.env.clear()` — use `self.env.transaction.clear()` or `self.env.transaction.reset()`.
- ❌ `from odoo.tools.cache import ormcache` — import from `odoo.api`: `from odoo.api import ormcache`.
- ❌ `escape_psql(...)` — use `escape_like_value(...)`.
- ❌ `type="base64"` on `<field file="..."/>` in XML — use `type="bytes"`.
- ❌ `<filter date="..." start_month="..." .../>` in search views — month/year range attributes removed.
- ❌ `static props = { ... }` in Owl components — use `props = useProps({ ... })` with `t` schema validators.
- ❌ `useState({ ... })` in Owl components — use `proxy({ ... })` or signals.
- ❌ `useService('xxx')` in Owl components — use `usePlugin(PluginClass)` as class fields.
- ❌ `<t t-slot="..."/>` — use `<t t-call-slot="..."/>`.
- ❌ `<t t-esc="..."/>` — use `<t t-out="..."/>`.
- ❌ Component variables without `this.` in Owl templates — all component state/props must have `this.`.
- ❌ `@http.route(..., type='json')` — use `@http.route(..., type='jsonrpc')`.
- ❌ Comparing booleans to non-booleans in domains (e.g. `[('active', '=', 1)]`) — use `[('active', '=', True)]`.
- ✅ Use `models.CachedModel` for stable cached tables.
- ✅ Use `compute_sql` for computed fields that need direct SQL query/filtering without storing.
- ✅ Use `('rel_field', 'access', 'operation')` in access domains to delegate security.

