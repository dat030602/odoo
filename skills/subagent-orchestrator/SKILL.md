---
name: subagent-orchestrator
description: "Master subagent dispatcher and coordinator. Use this skill when the user wants to coordinate, create, or invoke specialized subagents (163+ subagents across 10 categories) and attach their relevant AAS skills."
category: agent-orchestration
risk: safe
source: self
author: Antigravity Subagent Orchestrator
tags: [subagents, multi-agent, orchestration, skills, voltagent]
---

# Subagent Orchestrator & Dispatcher

## When to Use

Use this skill whenever:
- The user requests complex multi-faceted development (e.g. backend + frontend + DevOps + QA).
- The task requires specialized domain expertise (e.g. HIPAA compliance, Kubernetes orchestration, reverse engineering, machine learning).
- The user asks to delegate to a subagent or spawn parallel agents.
- The user asks to list, find, or activate subagents from the 163+ subagent fleet.

## Subagent Fleet Locations

- **Subagent Fleet Directory**: [`/opt/odoo19/.agents/agents/`](file:///opt/odoo19/.agents/agents/)
- **Main Agent Orchestrator**: [`/opt/odoo19/.agents/agents/main-agent-orchestrator.md`](file:///opt/odoo19/.agents/agents/main-agent-orchestrator.md)
- **Associated Skills Directory**: [`/opt/odoo19/.agents/skills/`](file:///opt/odoo19/.agents/skills/)

## Dispatch Workflow

1. **Identify Required Specialist(s)**:
   Consult [`main-agent-orchestrator.md`](file:///opt/odoo19/.agents/agents/main-agent-orchestrator.md) to select the subagent matching the domain.
2. **Review Associated Skills**:
   Inspect the subagent's definition in [`/opt/odoo19/.agents/agents/<name>.md`](file:///opt/odoo19/.agents/agents/) to see its pre-configured `skills:` list.
3. **Register / Define Subagent**:
   If not already defined in the active session, call `define_subagent` using the prompt and settings from the subagent's markdown file.
4. **Invoke Subagent**:
   Call `invoke_subagent` with the subagent's `TypeName`, `Role`, actionable `Prompt` (linking its associated skills), and `Model="inherit"`.
5. **Synthesize Results**:
   Receive outputs from subagents and deliver a clear, consolidated solution to the user.
