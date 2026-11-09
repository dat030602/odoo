# Odoo 20 Development Guide

This file provides guidance to AI agents when working with Odoo 20 code in this repository.

> **For setup instructions with different AI IDEs, see [AGENTS.md](./AGENTS.md)**

## Documentation Structure

The `skills/odoo-20.0/references/` directory contains modular guides for Odoo 20 development:

```
skills/odoo-20.0/
├── SKILL.md                       # Master index
├── references/                    # Development guides (19 files)
│   ├── api-highlights.md            # Version-distinguishing rules & checks
│   ├── odoo-20-actions-guide.md     # ir.actions.*, cron progress, bindings
│   ├── odoo-20-controller-guide.md  # HTTP, jsonrpc routing, GeoIP
│   ├── odoo-20-data-guide.md        # XML/CSV data files, type="bytes", eval
│   ├── odoo-20-decorator-guide.md   # @api decorators (@api.private, ormcache)
│   ├── odoo-20-development-guide.md # Manifest, wizards, module structure
│   ├── odoo-20-field-guide.md       # Field types, compute_sql, init_storage
│   ├── odoo-20-manifest-guide.md    # __manifest__.py reference & loading order
│   ├── odoo-20-mixins-guide.md      # mail.thread, activities, alias, utm
│   ├── odoo-20-model-guide.md       # ORM, CachedModel, Domain AST, search
│   ├── odoo-20-migration-guide.md   # Migration scripts, upgrade_code tool
│   ├── odoo-20-owl-guide.md         # OWL 3 components, useProps, proxy, plugins
│   ├── odoo-20-performance-guide.md # search_fetch, _read_group, N+1 prevention
│   ├── odoo-20-reports-guide.md     # QWeb reports, parametric t-call, t-out
│   ├── odoo-20-security-guide.md    # ir.access.csv, permissions, restrictions
│   ├── odoo-20-testing-guide.md     # TransactionCase, @odoo/hoot JS tests
│   ├── odoo-20-transaction-guide.md # Savepoints, transaction.clear, concurrency
│   ├── odoo-20-translation-guide.md # Translations, i18n, PO files
│   └── odoo-20-view-guide.md        # XML views (<list>, <form>, <search>)
├── CLAUDE.md                      # This file
└── AGENTS.md                      # AI agents setup
```

## Which Guide to Use

| Task                                  | Guide                                     |
| ------------------------------------- | ----------------------------------------- |
| Quick API checks / version changes    | `references/api-highlights.md`            |
| Configuring security (ACL, rules)     | `references/odoo-20-security-guide.md`    |
| Building OWL 3 components             | `references/odoo-20-owl-guide.md`         |
| Writing ORM queries / search domains  | `references/odoo-20-model-guide.md`       |
| Defining model fields / compute_sql   | `references/odoo-20-field-guide.md`       |
| Writing XML views                     | `references/odoo-20-view-guide.md`        |
| Upgrading modules / migrating data    | `references/odoo-20-migration-guide.md`   |
| Creating actions, menus, cron jobs    | `references/odoo-20-actions-guide.md`     |
| Creating HTTP / jsonrpc endpoints     | `references/odoo-20-controller-guide.md`  |
| Creating XML/CSV data files           | `references/odoo-20-data-guide.md`        |
| Creating a new module                 | `references/odoo-20-development-guide.md` |
| Configuring __manifest__.py           | `references/odoo-20-manifest-guide.md`    |
| Using @api decorators                 | `references/odoo-20-decorator-guide.md`   |
| Using mail.thread, activities, mixins | `references/odoo-20-mixins-guide.md`      |
| Fixing slow code / N+1 queries        | `references/odoo-20-performance-guide.md` |
| Creating QWeb reports                 | `references/odoo-20-reports-guide.md`     |
| Writing Python & JS tests             | `references/odoo-20-testing-guide.md`     |
| Handling transactions & cache         | `references/odoo-20-transaction-guide.md` |
| Adding translations / localization    | `references/odoo-20-translation-guide.md` |

## Key Odoo 20 Changes

1. **Security**: Access is defined solely in `security/ir.access.csv` (never `ir.model.access.csv` or XML `ir.rule`). Uses model name directly (e.g. `sale.order`) and `crud` letter subsets. Supports `'access'` operator.
2. **OWL 3**: Static `props` and `defaultProps` are ignored — use `props = useProps({ ... })` with `t` schema validators. `useState` is replaced with `proxy(...)` or signals. `useService` is replaced with `usePlugin(...)`. QWeb templates require `this.` for all component variables and methods.
3. **ORM & Models**: `models.CachedModel` caches stable datasets in memory. `compute_sql` allows direct SQL querying of computed fields. `_rec_names_search` is a tuple.
4. **Cache & Transactions**: `self.env.transaction.invalidate_ormcache()` replaces `registry.clear_cache()`. `self.env.transaction.clear()` replaces `self.env.clear()`.
5. **Views**: Search view date filters do not use range attributes (`start_month`, `end_month`, `start_year`, `end_year`).
6. **Data**: XML binary files use `type="bytes"` instead of `type="base64"`.

