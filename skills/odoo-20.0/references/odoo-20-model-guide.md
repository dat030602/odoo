# Odoo 20 Model Guide

## Python and Odoo Conventions

- Order declarations: private attributes (`_name`, `_description`, `_inherit`, `_table_objects`), defaults, fields, compute/inverse/search methods, constraints, CRUD overrides, actions, then business methods.
- Keep `_name` explicit on new models.
- Declare `_rec_names_search` as a **tuple**, e.g. `_rec_names_search = ('name', 'code')`.
- Use `models.CachedModel` for tables with small, stable reference datasets (`res.country`, `res.currency`).
- Declare table constraints and indexes via `models.Constraint`, `models.Index`, and `models.UniqueIndex` (never `_sql_constraints`).
- In search domains, compare booleans only with booleans: `[('active', '=', True)]`.
- Call `concat()` and `union()` on an empty recordset with a single iterable: `self.env['my.model'].concat([recs1, recs2])`.
- Invalidate caches via `self.env.transaction.invalidate_ormcache()` and reset via `self.env.transaction.clear()`.
- Use `escape_like_value()` instead of `escape_psql()`.

---

## Table of Contents

- [Defining Models](#defining-models)
- [Cached Models (`models.CachedModel`)](#cached-models-modelscachedmodel)
- [Table Constraints & Indexes](#table-constraints--indexes)
- [Search Domains & The `Domain` Class](#search-domains--the-domain-class)
- [CRUD Operations & Recordsets](#crud-operations--recordsets)
- [Transaction & Cache Management](#transaction--cache-management)
- [SQL Execution](#sql-execution)

---

## Defining Models

### Standard Model Classes

| Class | Purpose | Database Table |
|-------|---------|----------------|
| `models.Model` | Regular business model | Yes (persistent) |
| `models.TransientModel` | Wizard / temporary data | Yes (auto-vacuumed) |
| `models.AbstractModel` | Mixin / base functionality | No |
| `models.CachedModel` | In-memory cached reference data | Yes (persistent, cached in memory) |

### Defining a Model

```python
from odoo import api, fields, models

class ProjectTask(models.Model):
    _name = 'project.task'
    _description = 'Project Task'
    _order = 'sequence, id desc'
    _rec_names_search = ('name', 'code')  # Must be a tuple

    name = fields.Char(string="Task Title", required=True)
    code = fields.Char(string="Reference Code", copy=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string="Assignee")
```

### SQL View Models (Replacing `_table_query`)

In Odoo 20, `_table_query` has been removed. SQL view models (`_auto = False`) must implement `@property def _table_sql(self) -> SQL:`:

```python
from odoo import fields, models
from odoo.tools import SQL

class TaskAnalysisReport(models.Model):
    _name = 'task.analysis.report'
    _description = 'Task Analysis Report'
    _auto = False
    _order = 'date desc'

    task_id = fields.Many2one('project.task', readonly=True)
    user_id = fields.Many2one('res.users', readonly=True)
    date = fields.Date(readonly=True)
    task_count = fields.Integer(readonly=True)

    @property
    def _table_sql(self) -> SQL:
        """Define SQL query building the database view."""
        return SQL(
            """
            SELECT
                min(t.id) AS id,
                t.id AS task_id,
                t.user_id AS user_id,
                t.date_deadline AS date,
                count(*) AS task_count
            FROM project_task t
            GROUP BY t.id, t.user_id, t.date_deadline
            """
        )
```

---

## Cached Models (`models.CachedModel`)

`models.CachedModel` provides high-performance, process-wide in-memory caching for models whose records rarely change (e.g. `res.country`, `res.currency`, `res.lang`, `website`).

### Defining a CachedModel

```python
from odoo import fields, models

class ProductCategory(models.CachedModel):
    _name = 'product.category'
    _description = 'Product Category'

    # Specify which fields to cache in memory across requests
    _cached_data_fields = ('name', 'parent_id', 'complete_name')

    # Optional domain filter for records to cache (defaults to all)
    _cached_data_domain = [('active', '=', True)]

    name = fields.Char(required=True)
    parent_id = fields.Many2one('product.category')
    complete_name = fields.Char()
```

### Accessing Cached Data

```python
# Fetch all cached records without hitting PostgreSQL:
all_categories = self.env['product.category'].get_all()
```

---

## Table Constraints & Indexes

Declare SQL constraints and database indexes as class attributes starting with `_` using `models.Constraint`, `models.Index`, and `models.UniqueIndex`:

```python
from odoo import models, fields

class AccountAccount(models.Model):
    _name = 'account.account'
    _description = 'Account'

    code = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True)
    active = fields.Boolean(default=True)

    # Unique constraint on (code, company_id)
    _unique_code_per_company = models.Constraint(
        'UNIQUE(code, company_id)',
        "The code of the account must be unique per company!",
    )

    # Partial unique index (only for active records)
    _unique_active_code = models.UniqueIndex(
        '(code, company_id) WHERE active',
        "The code must be unique among active accounts!",
    )

    # Performance database index
    _idx_company_code = models.Index('(company_id, code)')
```

---

## Search Domains & The `Domain` Class

Odoo 20 processes domains using an AST-based `Domain` class (`from odoo.fields import Domain` or `from odoo.orm.domains import Domain`).

### Basic Search and Dynamic Dates

Domains can contain native dynamic date tokens:

```python
# 'now', 'today', '+1d', '=1d'
domain = [
    ('state', '=', 'done'),
    ('date_deadline', '<=', 'today'),
    ('create_date', '>=', 'today -7d'),
    ('active', '=', True),  # Always compare booleans with True/False
]
records = self.search(domain)
```

### Relational Operators (`any`, `not any`)

Traverse relationships cleanly:

```python
# Matches sales orders having any line for product_id 10:
orders = self.env['sale.order'].search([
    ('order_line', 'any', [('product_id', '=', 10), ('price_unit', '>', 100)]),
])
```

### The `Domain` AST Operations

```python
from odoo.fields import Domain

d1 = Domain([('state', '=', 'draft')])
d2 = Domain([('user_id', '=', self.env.uid)])

# Combine with bitwise operators
combined = d1 & d2   # AND
either = d1 | d2     # OR
inverted = ~d1       # NOT

# Class helper methods
all_active = Domain.AND([d1, d2, Domain([('active', '=', True)])])
any_option = Domain.OR([d1, d2])

# Boolean constants
Domain.TRUE
Domain.FALSE
```

---

## CRUD Operations & Recordsets

### Multi-Create

Always use `@api.model_create_multi`:

```python
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if not vals.get('code'):
            vals['code'] = self.env['ir.sequence'].next_by_code('my.sequence')
    return super().create(vals_list)
```

### Recordset Concatenation & Union

Call `concat()` or `union()` on an empty recordset with a single iterable:

```python
# Correct in Odoo 20:
all_records = self.env['my.model'].concat([recs_a, recs_b, recs_c])
unique_records = self.env['my.model'].union([recs_a, recs_b])

# Avoid deprecated multi-argument usage:
# recs_a.concat(recs_b)  # Deprecated warning in 20.0
```

### High-Performance Aggregations (`_read_group`)

```python
# Returns list of tuples
data = self.env['sale.order']._read_group(
    domain=[('state', '=', 'sale')],
    groupby=['partner_id'],
    aggregates=['amount_total:sum', 'id:count'],
)
for partner, total_sum, order_count in data:
    print(f"Partner {partner.name}: {order_count} orders totaling {total_sum}")
```

---

## Transaction & Cache Management

### Invalidation

```python
# Invalidate ORM cache (replaces registry.clear_cache):
self.env.transaction.invalidate_ormcache()

# Invalidate specific cache:
self.env.transaction.invalidate_ormcache('stable')

# Clear/reset transaction caches:
self.env.transaction.clear()
self.env.transaction.reset()

# Invalidate security access cache:
self.env.invalidate_access_cache()
```

### Cache Decorator

Import `ormcache` directly from `odoo.api`:

```python
from odoo import api

class MyModel(models.Model):
    _name = 'my.model'

    @api.ormcache('key')
    def get_data(self, key):
        # Expensive calculation
        return compute_expensive_data(key)
```

---

## SQL Execution

Always use parameterized `odoo.tools.SQL` queries:

```python
from odoo.tools import SQL, escape_like_value

# Parameterized query
self.env.cr.execute(
    SQL(
        "SELECT id, name FROM %s WHERE active = %s AND name LIKE %s",
        SQL.identifier(self._table),
        True,
        f"%{escape_like_value(search_str)}%",
    )
)
results = self.env.cr.dictfetchall()
```

