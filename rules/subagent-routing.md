---
trigger: always_on
description: Anti-fabrication + planner-first gate. The planner classifies every request into a tier, loads the odoo-routing skill for full pipeline rules, and returns a checklist. The coordinator executes exactly what the planner prescribes.
---

# Subagent Routing + Anti-Fabrication (always on)

## 1. Never fabricate

- Never invent or guess: Odoo models, fields, methods, view/xpath targets, CLI flags, file paths,
  agent or skill names, tool results, test results, or command output.
- A claim is allowed only if you verified it in this session (read the source, ran the command,
  received the RPC/tool response). Otherwise say plainly "not verified" and verify it, or ask the user.
- Never describe a subagent run, test run or tool call that did not actually happen.

## 2. Skills index

`./.agents/skills_index.json` — JSON array. Each entry: `id`, `path`, `category`, `name`, `description`, `risk`.
- Never load it whole. Search by keyword:
  ```
  jq -r '.[] | select((.name+" "+.category+" "+.description) | test("kw1|kw2";"i")) | [.id,.name,.description] | @tsv' ./.agents/skills_index.json | head -20
  ```
- Try keywords in English and Vietnamese. Read the full `description` before choosing.
- If `risk` ≠ `safe`: tell the user and wait for approval before using.

## 3. Planner is the gatekeeper — always invoke planner first

**Before any subagent does work, the `planner` must run.**

The planner:
1. Reads `.agents/skills/odoo-routing/SKILL.md` for the full pipeline execution rules.
2. Classifies the request into a tier.
3. Returns a checklist specifying exactly which stages and subagents are needed.

The coordinator (you) must follow the planner's checklist exactly. Do not add or skip stages on your own.

### Tier definitions (the planner decides the tier)

| Tier | Examples | Required stages |
|------|----------|-----------------|
| **Q** — Question / explanation | "giải thích X là gì", "tại sao lỗi Y", đọc code | PLAN only (planner answers inline, no subagent needed) |
| **T** — Trivial change | Sửa label, thêm 1 field không có logic, fix typo XML | PLAN → EXECUTE |
| **S** — Small change | 2–5 fields + views, no business logic, no migration | PLAN → EXECUTE → REVIEW |
| **M** — Medium | New model, business logic, security, computed fields | PLAN → EXECUTE → REVIEW → TEST |
| **L** — Large | Multiple models, migrations, integrations, accounting entries | PLAN → EXECUTE → REVIEW → TEST (each milestone) |

**Tier escalation rule:** if EXECUTE reveals the change is bigger than the tier, EXECUTE must stop and report to the coordinator, who returns to PLAN — never silently expands scope.

## 4. Full pipeline rules

All detailed operational rules (skills index usage, stage separation, Chrome DevTools UI check,
stage gates, failure loops, skill discovery, subagent selection, delegation hygiene) are in:

**`/opt/odoo19/.agents/skills/odoo-routing/SKILL.md`**

The planner must read this skill before producing any checklist.
The coordinator must follow these rules when dispatching subagents.
