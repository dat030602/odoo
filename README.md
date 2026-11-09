# .agents — AI Agent Configuration

This folder contains the AI agent configuration for the Odoo workspace: rules, agents, and skills used by [Antigravity](https://antigravity.dev) (and compatible tools such as Claude Code).

## Folder Structure

```
.agents/
├── .env.local              # Local config: MODULE_PREFIX, AUTHOR, ODOO_VERSION (not committed)
├── .gitignore
├── .mcp.json               # MCP server configuration
│
├── agents/                 # Subagent definitions (one .md per role)
│   ├── planner.md          # Read-only analyst — turns requests into verified plans
│   ├── odoo-coder.md       # Implements features from the approved plan
│   ├── odoo-code-review.md # Scores and flags issues in diffs/PRs
│   ├── odoo-code-tracer.md # Traces execution flow end-to-end
│   ├── tester.md           # Writes and runs tests, verifies acceptance criteria
│   ├── build-error-resolver.md
│   ├── doc-updater.md
│   └── security-reviewer.md
│
├── rules/                  # Always-on rules loaded for every agent
│   ├── subagent-routing.md # Mandatory 4-stage pipeline (PLAN→EXECUTE→REVIEW→TEST)
│   ├── dn-module-standards.md  # Module prefix, author, version, file structure
│   ├── coding-style.md     # Import order, naming conventions
│   └── security.md         # Security checklist applied to every commit
│
└── skills/                 # Optional knowledge packs loaded on demand
    ├── odoo-17.0/          # Odoo 17 reference guides (models, views, security, …)
    ├── odoo-18.0/          # Odoo 18 reference guides
    ├── odoo-19.0/          # Odoo 19 reference guides  ← active version
    ├── odoo-20.0/          # Odoo 20 reference guides
    ├── odoo-commit/        # Commit message conventions (Odoo git style)
    ├── odoo-module-index-html/  # Guide for static/description/index.html
    ├── odoo-test/          # Unit test runner, XML-RPC scenarios, multi-user test patterns
    ├── odoo-workflow/      # Pre-code gate: trace source before planning
    ├── dtg-base/           # DTGBase abstract model utilities reference
    ├── security-review/    # Security checklist for sensitive features
    └── tdd-workflow/       # TDD workflow enforcement
```

## Workflow

Every task goes through **4 mandatory stages** (defined in `rules/subagent-routing.md`):

```
PLAN  →  EXECUTE  →  REVIEW  →  TEST
```

Each stage is a separate subagent invocation. REVIEW must return `APPROVED` and TEST must return `PASS` before a task is considered done.

## Local Configuration

Project defaults live in `.env.local` (excluded from git — copy from the table below):

| Key             | Description                                      | Default |
|-----------------|--------------------------------------------------|---------|
| `MODULE_PREFIX` | Required prefix for all custom module names      | `dn_`   |
| `AUTHOR`        | Value of `author` in every module manifest       | `Dyan`  |
| `ODOO_VERSION`  | Target Odoo series for this workspace            | `19.0`  |

Create your own `.env.local`:

```bash
cp /dev/stdin .agents/.env.local <<'EOF'
MODULE_PREFIX=dn_
AUTHOR=Dyan
ODOO_VERSION=19.0
EOF
```

## Key Rules

### Module file structure
Each model is **one file** — both Python and XML:
- `models/<model_name>.py` — one `Model` class only
- `views/<model_name>_views.xml` — views for that model only

### Security groups
Agents must **never create a new `res.groups` record** unless explicitly requested. Using existing groups (`stock.group_stock_user`, `account.group_account_user`, etc.) in `groups=` attributes or ACL rows is always allowed.

### UI access guards
Every button or menu that opens a cross-domain view (e.g. warehouse → Journal Entry) **must** carry a `groups=` attribute matching the target model's access group. Missing guards cause the `window action not found` error at runtime.

### Multi-user testing
Tests must cover **at least two user roles**: the primary operational user (e.g. warehouse) and a user without cross-domain access (e.g. no accounting group). Tests that only run as admin are incomplete.

## Adding or Updating Content

| What you want to change | File to edit |
|-------------------------|--------------|
| Project defaults (prefix, author, version) | `.env.local` |
| Agent behaviour / hard rules | `agents/<agent>.md` |
| Always-on conventions | `rules/<rule>.md` |
| Odoo API reference for a version | `skills/odoo-<version>/references/` |
| Test runner instructions | `skills/odoo-test/SKILL.md` |
| Code review criteria | `agents/odoo-code-review.md` |
