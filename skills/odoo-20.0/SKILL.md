---
name: odoo-20
description: >-
  Odoo 20 development knowledge base with 19 specialized guides covering
  Unified Security & ACL (ir.access, security/ir.access.csv, permissions vs
  restrictions, 'access' operator), OWL 3 Components (useProps, proxy, signals,
  plugins replacing services, this. template syntax, t-call-slot, t-out),
  Models & ORM (models.CachedModel, compute_sql, init_storage, Domain AST,
  _rec_names_search tuple, transaction cache invalidation), Actions
  (ir.actions.*, cron _commit_progress, server actions), Controllers (HTTP
  routing, type='jsonrpc', object-based GeoIP), Data files (type='bytes'
  replacing base64, parametric t-call, dynamic dates in domains), API
  Decorators (@api.depends, @api.constrains, @api.ondelete, @api.model_create_multi,
  @api.private, @api.readonly, @api.ormcache from odoo.api), SQL Constraints
  and Indexes (models.Constraint, models.Index, models.UniqueIndex), Module
  development (manifest, wizards, reports), Field types (Char, Monetary,
  relational, Json, Properties), Mixins (mail.thread, mail.activity.mixin,
  mail.alias.mixin, utm.mixin), Migration scripts (upgrade_code, v19 to v20
  conversions), Performance optimization (search_fetch, _read_group, N+1
  prevention), QWeb Reports (parametric t-call, t-out, barcodes), Testing
  (TransactionCase, HttpCase, @odoo/hoot JS test framework), Transactions
  (savepoints, transaction.clear), Translations (i18n, PO files, translatable
  fields), XML Views (list tag, direct-expression attrs, kanban card templates,
  search view date filters without range attrs). Use when writing, reviewing,
  or debugging any Odoo 20 Python, JS, XML or CSV code.
globs: "**/*.{py,xml,csv,js,ts,css,scss}"
---

# Odoo 20 Skill - Master Index

Master index for all Odoo 20 development guides. Read the appropriate guide from `references/` based on your task.

## Quick Reference

| Topic          | File                                      | When to Use                                             |
| -------------- | ----------------------------------------- | ------------------------------------------------------- |
| API Highlights | `references/api-highlights.md`            | Quick review checks, version changes, deprecated APIs   |
| Security & ACL | `references/odoo-20-security-guide.md`    | `ir.access.csv`, permissions, restrictions, access check|
| OWL 3          | `references/odoo-20-owl-guide.md`         | OWL 3 components, `useProps`, `proxy`, signals, plugins |
| Models & ORM   | `references/odoo-20-model-guide.md`       | ORM queries, `CachedModel`, Domain AST, search filters  |
| Field Types    | `references/odoo-20-field-guide.md`       | Defining fields, `compute_sql`, `init_storage`, params  |
| Views & XML    | `references/odoo-20-view-guide.md`        | XML views (`<list>`, `<form>`, `<search>`, `<kanban>`)  |
| Migration      | `references/odoo-20-migration-guide.md`   | Upgrading modules from v19 to v20, `upgrade_code` tool  |
| Actions & Cron | `references/odoo-20-actions-guide.md`     | Creating actions, menus, scheduled jobs (`ir.cron`)     |
| Controllers    | `references/odoo-20-controller-guide.md`  | Writing HTTP / `jsonrpc` endpoints, web controllers     |
| Data Files     | `references/odoo-20-data-guide.md`        | XML/CSV records, `type="bytes"`, parametric `t-call`    |
| Development    | `references/odoo-20-development-guide.md` | Creating new modules, module structure, wizards         |
| Manifest       | `references/odoo-20-manifest-guide.md`    | `__manifest__.py` configuration, dependencies, assets   |
| API Decorators | `references/odoo-20-decorator-guide.md`   | Using `@api` decorators, compute, validation, `@api.private`|
| Mixins         | `references/odoo-20-mixins-guide.md`      | `mail.thread`, chatter, activities, email aliases, UTM  |
| Performance    | `references/odoo-20-performance-guide.md` | Optimizing queries, fixing slow code, `search_fetch`    |
| Reports        | `references/odoo-20-reports-guide.md`     | QWeb reports, PDF/HTML, templates, paper formats        |
| Testing        | `references/odoo-20-testing-guide.md`     | Python `TransactionCase` & `@odoo/hoot` JS unit tests   |
| Transactions   | `references/odoo-20-transaction-guide.md` | Savepoints, error handling, cache reset, concurrency    |
| Translation    | `references/odoo-20-translation-guide.md` | Adding translations, localization, i18n, PO files       |

## Coding Conventions

Before writing code, run the `odoo-workflow` skill if it is installed (trace the real source, Context Brief with `file:line`, definition of done).

Read `references/api-highlights.md` before writing code and apply its Quick review checks: the ❌ items are what not to use in Odoo 20.

- **Security**: Defined strictly in `security/ir.access.csv` (never `ir.model.access.csv` or standalone `ir.rule` XML records).
- **OWL 3**: Declare props via `props = useProps({ ... })`, state via `proxy(...)` or signals, and plugins via `usePlugin(...)`. Always prefix component variables with `this.` in templates.
- **ORM & Models**: Model names explicit; table objects via `models.Constraint`/`models.Index`; `_rec_names_search` as a tuple; cached models inherit `models.CachedModel`.
- **Views**: `<list>` tag; direct expression modifiers (never `attrs=`); search date filters without range attributes.
- **Data**: XML binary files use `type="bytes"` (never `type="base64"`).

## File Structure

```
skills/odoo-20.0/
├── SKILL.md                          # This file - master index
├── AGENTS.md                         # AI agents setup instructions
├── CLAUDE.md                         # Claude Code instructions
└── references/                       # Development guides (19 files)
    ├── api-highlights.md
    ├── odoo-20-actions-guide.md
    ├── odoo-20-controller-guide.md
    ├── odoo-20-data-guide.md
    ├── odoo-20-decorator-guide.md
    ├── odoo-20-development-guide.md
    ├── odoo-20-field-guide.md
    ├── odoo-20-manifest-guide.md
    ├── odoo-20-migration-guide.md
    ├── odoo-20-mixins-guide.md
    ├── odoo-20-model-guide.md
    ├── odoo-20-owl-guide.md
    ├── odoo-20-performance-guide.md
    ├── odoo-20-reports-guide.md
    ├── odoo-20-security-guide.md
    ├── odoo-20-testing-guide.md
    ├── odoo-20-transaction-guide.md
    ├── odoo-20-translation-guide.md
    └── odoo-20-view-guide.md
```

## Base Code Reference (Odoo 20)

All guides are based on analysis of the Odoo 20 source code (`odoo/` and `addons/`).

