# Meta Migrator (Odoo 19)

Technical module for migrating custom models and fields, views, server actions, window
actions, menus, access rights, and record rules from a source Odoo system to a target
through XML-RPC.

## Installation

Copy `meta_migrator` into an addons path and install it as a normal module. Users need
the `base.group_system` technical settings permission.

## Workflow

1. Create reusable source and target records under **Meta Migrator > Connections**.
2. Create a job under **Meta Migrator > Migration Jobs**, select the connections, and
   choose a conflict policy.
3. Choose one job type:
   - **Model Only**: enter model lines. Models and custom fields are migrated. Optional
     access rights and record rules can be copied after the fields are ready. Enter a
     target model name to rename the model; the mapping is saved for later content jobs.
   - **Field / View / Server Action**: enable any combination of Fields, Views, and
     Server Actions. Each enabled type has its own input lines and runs independently.
4. Run the job. Each line and the aggregate log record its result.

Enable **Create Menus** to enter only a technical model name. The migrator finds source
window actions for that model and creates or updates their related menus on the target.
Model-only jobs use the existing model lines; content jobs use the Menus tab.

## Field processing

Fields use two passes. Pass 1 writes core properties and creates one2many fields last so
their relation fields exist first. Pass 2 writes `compute`, `depends`, and `related` after
all fields in the model exist. Field jobs only accept source fields with `state = manual`.

## Views and security

View jobs select active source views with the lowest priority for each selected type. The
source arch is copied as an independent target view. Access rights and record rules map
groups by XML ID, skip records whose custom groups cannot be mapped, and preserve rule
domains verbatim. A rule with source groups that all fail mapping remains restricted to an
empty group set rather than becoming global.

## Limitations

Content jobs never create target models; run a **Model Only** job first. Model rename maps
are retained per source/target connection pair and used for relational fields and server
actions. View arch expressions and rule domain strings are not rewritten. Passwords are
stored in a normal Char field, so access to the connection model should remain restricted.
Both Odoo servers must expose `/xmlrpc/2/common` and `/xmlrpc/2/object` to this server.
