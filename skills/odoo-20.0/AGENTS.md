# Odoo 20 Documentation - AI Agents Setup

Setup guide for using Odoo 20 documentation with AI coding assistants (Cursor, Claude Code, Windsurf, Antigravity, Aider, etc.).

## Quick Start

### Installation

To add the Odoo 20 skill pack to your environment:

```bash
# Add Odoo 20 skill to your project
npx skills add unclecatvn/agent-skills
```

### Cursor IDE - Remote Rule

Configure once in Cursor settings:
- `Settings` → `Rules` → `Add Remote Rule`
- Source: `Git Repository`
- URL: `git@github.com:unclecatvn/agent-skills.git`
- Branch: `20.0`
- Subfolder: `skills/odoo-20.0/`

---

## Documentation Structure

```
skills/odoo-20.0/
├── SKILL.md                       # Master index (all agents)
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
├── CLAUDE.md                      # Claude Code specific guide
└── AGENTS.md                      # THIS FILE - setup guide
```

---

## Guide Reference

| File | Purpose | When to Use |
|------|---------|-------------|
| `references/api-highlights.md` | API diff & version checks | Quick review checks, version changes, deprecated APIs |
| `references/odoo-20-security-guide.md` | Security and access rights | `ir.access.csv`, permissions, restrictions, access check |
| `references/odoo-20-owl-guide.md` | OWL 3 web components | OWL 3 components, `useProps`, `proxy`, signals, plugins |
| `references/odoo-20-model-guide.md` | ORM models & operations | ORM queries, `CachedModel`, Domain AST, search filters |
| `references/odoo-20-field-guide.md` | Field definitions & types | Defining fields, `compute_sql`, `init_storage`, parameters |
| `references/odoo-20-view-guide.md` | XML views & user interfaces | XML views (`<list>`, `<form>`, `<search>`, `<kanban>`) |
| `references/odoo-20-migration-guide.md` | Version upgrades & migration | Upgrading modules from v19 to v20, `upgrade_code` tool |
| `references/odoo-20-actions-guide.md` | Actions, menus & cron | Creating actions, menus, scheduled jobs (`ir.cron`) |
| `references/odoo-20-controller-guide.md` | HTTP & JSON-RPC routes | Writing HTTP / `jsonrpc` endpoints, web controllers |
| `references/odoo-20-data-guide.md` | Data records & XML/CSV | XML/CSV records, `type="bytes"`, parametric `t-call` |
| `references/odoo-20-development-guide.md` | Module development overview | Creating new modules, module structure, wizards |
| `references/odoo-20-manifest-guide.md` | Manifest configuration | `__manifest__.py` configuration, dependencies, assets |
| `references/odoo-20-decorator-guide.md` | Python `@api` decorators | Using `@api` decorators, compute, validation, `@api.private` |
| `references/odoo-20-mixins-guide.md` | Pre-built mixins | `mail.thread`, chatter, activities, email aliases, UTM |
| `references/odoo-20-performance-guide.md` | Performance & query optimization | Optimizing queries, fixing slow code, `search_fetch` |
| `references/odoo-20-reports-guide.md` | QWeb reporting | QWeb reports, PDF/HTML, templates, paper formats |
| `references/odoo-20-testing-guide.md` | Unit & integration testing | Python `TransactionCase` & `@odoo/hoot` JS unit tests |
| `references/odoo-20-transaction-guide.md` | Database transactions | Savepoints, error handling, cache reset, concurrency |
| `references/odoo-20-translation-guide.md` | Internationalization | Adding translations, localization, i18n, PO files |

