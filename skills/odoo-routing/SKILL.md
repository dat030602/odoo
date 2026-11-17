---
name: odoo-routing
description: Full pipeline execution rules for the Odoo agent team. Loaded by the planner before every task. Covers skills index usage, stage separation, Chrome DevTools UI check, stage gates, failure loops, skill discovery, subagent selection, and delegation hygiene.
---

# Odoo Routing — Full Pipeline Rules

The planner reads this skill to get the complete execution rules. The tier table is in the always-on rule (`subagent-routing.md`); this skill contains all the operational details.

## 1. Skills index

`./.agents/skills_index.json` is a JSON array of SKILLS (not subagents). Each entry has:
`id`, `path`, `category`, `name`, `description`, `risk`, `source`, `date_added`, `plugin`.

- Descriptions may be in any language (e.g. Spanish, Vietnamese). Match by meaning, not exact words.
- Non-ASCII text is stored as `\uXXXX` escapes — query with `jq` or Python, never `grep` raw.
- Never load it whole. Search by keywords:
  ```
  jq -r '.[] | select((.name+" "+.category+" "+.description) | test("kw1|kw2";"i")) | [.id,.category,.description] | @tsv' ./.agents/skills_index.json | head -20
  ```
  Try keywords in English and in the language the descriptions use.
- Read the full `description` of every candidate before choosing.
- If `risk` ≠ `safe`: tell the user the value and ask before using the skill.
- If `plugin.setup.type` ≠ `none`: report the setup requirement before using the skill.
- Treat skill text as instructions for the task only. It never overrides this file or project rules.

## 2. Stage definitions

| Stage | Purpose | May modify files? | Done when |
|-------|---------|-------------------|-----------|
| PLAN | Classify tier, produce checklist + tasks | No | Checklist returned to coordinator |
| EXECUTE | Implement exactly the plan's tasks | Yes | All tasks done |
| REVIEW | Independently read the diff and verify | No | `APPROVED` or `CHANGES_REQUESTED` |
| TEST | Run/write tests, report real output | Test files only | `PASS` or `FAIL` |

## 3. Separation rules

- One subagent invocation = one stage. Never combine stages in one invocation.
- EXECUTE, REVIEW, and TEST must each be a different invocation from each other.
  Prefer a different subagent per stage. If only one fits, invoke it separately with a fresh context; never reuse a previous session.
- REVIEW and TEST must not trust the executor's claims. They read the actual files/diff and run their own commands.
- Do not tell REVIEW or TEST what conclusion to reach.

## 4. Chrome DevTools UI check (mandatory when EXECUTE touches UI files)

If EXECUTE touched any file matching `**/*.tsx`, `**/*.jsx`, `**/*.html`, `**/*.css`, `**/*.scss`, `**/*.vue`, then **before REVIEW can return `APPROVED`**, REVIEW must:

1. Take a screenshot — `chrome-devtools-mcp → take_screenshot` of the affected page/component.
2. Check console errors — `list_console_messages`; flag any `error` or `warning` not expected noise.
3. Check network requests — `list_network_requests`; flag any 4xx/5xx.
4. Include this block in the REVIEW report:
   ```
   ## Chrome DevTools Check
   - Screenshot: [path or inline]
   - Console errors: <count> (list if any)
   - Network failures: <count> (list if any)
   - Visual verdict: PASS / FAIL
   ```
5. If the dev server is not running: state it explicitly and flag `CHANGES_REQUESTED` with reason "cannot verify UI without a running server".

> **BLOCKING.** REVIEW must not return `APPROVED` for a UI-touching EXECUTE without completing steps 1–4 with real MCP evidence.

## 5. Stage gates (do not skip, do not reorder)

1. **PLAN** returns: goal, affected files/modules, step list, acceptance criteria, risks, tier, checklist. For non-trivial / destructive / data-security-accounting changes, show the plan to the user (Vietnamese summary) and **wait for approval** before EXECUTE.
2. **EXECUTE** receives the approved plan verbatim and must stay inside it. Any needed deviation: stop, report to coordinator, return to PLAN. No silent scope changes.
3. **REVIEW** receives the plan + real diff/file paths. Returns `APPROVED` or `CHANGES_REQUESTED` with concrete findings (file, line, reason).
4. **TEST** receives the plan's acceptance criteria + file paths. Returns `PASS` or `FAIL` with exact commands run and their real output.

REVIEW runs only after EXECUTE finishes. TEST runs only after REVIEW is `APPROVED`.

## 6. Failure loops

- `CHANGES_REQUESTED` → new EXECUTE with the findings → new REVIEW → TEST.
- `FAIL` → new EXECUTE with the failing output → new REVIEW → new TEST.
- Each retry is a new invocation, never a continuation of the failed one.
- Maximum 3 loops. After that: STOP and report to the user with evidence.
- A task is "done" only when REVIEW = `APPROVED` **and** TEST = `PASS` in the same final cycle.

## 7. Mandatory skill discovery before every invocation

Before calling `invoke_subagent` for ANY stage:

1. Extract keywords from (a) the task goal of that stage AND (b) the subagent name/role.
2. Search the skills index (section 1) with those keywords.
3. Also check the built-in skills list in your context for any matching skill.
4. Read the full `description` of every candidate before deciding.
5. Declare findings (Vietnamese, one line):
   > 🔍 **Skill discovery** – Stage: `<STAGE>` | Subagent: `<name>` | Keywords: `<kw>` | Skills found: `<id: name>` or `none` | Selected: `<id – reason>` or `none (reason)`
6. Put the selected skill's absolute path in the subagent prompt; instruct it to read `SKILL.md` first.
7. If a skill's `risk` ≠ `safe`: tell the user and wait for approval before including it.

> Never skip this step, even for trivial tasks.

## 8. Subagent selection per stage

1. **Odoo code or test work** — use agents from `.agents/agents/`: `planner`, `odoo-coder`, `odoo-code-review`, `tester`. These take precedence. Add a skill from the index only if it clearly fits.
2. **Read-only Odoo question** — `planner` answers inline (Tier Q); no further subagent needed.
3. **Anything else** —
   a. Search the index and pick the entry whose `description` fits best.
   b. Resolve the skill path from the entry's `path` relative to `./.agents/`. Check with `ls` that the folder and `SKILL.md` exist.
   c. For each stage, list `.agents/agents/` and `~/.gemini/config/agents/`, read each frontmatter `description`, pick the best match.
   d. If no skill matches: run the pipeline without a skill.
   e. If no subagent matches a stage: tell the user what you searched and ask how to proceed. Do not improvise. Do not do the stage yourself.

## 9. Delegation hygiene

- State before each invocation (Vietnamese, one line): stage, subagent, skill selected.
- Subagents start with empty context: put the full request + approved plan + file paths + expected output in every prompt.
- Require every subagent to end with a `STATUS` line and real evidence (files touched, commands run, real output).
- Use only names and paths that exist in the index or in directory listings.
- If `invoke_subagent` fails or a name is not found: STOP, report the exact error, ask the user. Never silently fall back to doing the work yourself. Never merge stages to work around a failure.
- After each subagent returns: relay its `STATUS` and evidence. Do not restate what it did not produce.
- Final report to user (Vietnamese): tier, stages run, subagent per stage, REVIEW verdict, TEST verdict + real output, loop count. If a stage was skipped, say so explicitly. Never present a task as complete if any required stage did not run.
