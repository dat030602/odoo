# Odoo 20 Performance Guide

Guide for optimizing performance, eliminating N+1 queries, and scaling Odoo 20 modules.

## Table of Contents

- [Core Performance Strategies](#core-performance-strategies)
- [Preventing N+1 Queries with `search_fetch`](#preventing-n1-queries-with-search_fetch)
- [SQL-Level Computes (`compute_sql`)](#sql-level-computes-compute_sql)
- [In-Memory Caching (`models.CachedModel`)](#in-memory-caching-modelscachedmodel)
- [Database Aggregations (`_read_group`)](#database-aggregations-_read_group)
- [Database Indexes (`models.Index`)](#database-indexes-modelsindex)
- [Method Caching with `@api.ormcache`](#method-caching-with-apiormcache)

---

## Core Performance Strategies

1. **Avoid looping queries**: Never execute ORM queries (`search`, `browse`, or relational field dot-walks) inside a Python loop.
2. **Push computation to SQL**: Use `compute_sql` for computed fields that need to be searched or sorted.
3. **Use `models.CachedModel`**: Keep stable lookup tables in memory.
4. **Index search fields**: Create targeted database indexes using `models.Index`.
5. **Batch operations**: Use `@api.model_create_multi` and `create(vals_list)`.

---

## Preventing N+1 Queries with `search_fetch`

When you only need specific fields on a set of records, use `search_fetch()` to load the exact fields in a single query:

```python
# Optimal: Only queries the specified fields
partners = self.env['res.partner'].search_fetch(
    domain=[('customer_rank', '>', 0)],
    field_names=['name', 'email', 'commercial_partner_id'],
    order='name asc',
    limit=100,
)
```

---

## SQL-Level Computes (`compute_sql`)

Traditional non-stored computed fields require Python loops when filtering:
```python
# SLOW: Loops through all records in Python
orders = self.env['sale.order'].search([]).filtered(lambda o: o.has_discounted_lines)
```

Using `compute_sql` executes the entire check directly in PostgreSQL in one fast query:

```python
has_discounted_lines = fields.Boolean(
    compute='_compute_has_discounted_lines',
    compute_sql='_compute_sql_has_discounted_lines',
    compute_sudo=True,
)

def _compute_sql_has_discounted_lines(self, table):
    return SQL(
        """EXISTS (
            SELECT 1 FROM sale_order_line sol
            WHERE sol.order_id = %s AND sol.discount > 0
        )""",
        table.id,
    )

# FAST: Executed in SQL directly:
orders = self.env['sale.order'].search([('has_discounted_lines', '=', True)])
```

---

## In-Memory Caching (`models.CachedModel`)

For lookup models that are read thousands of times per request but rarely modified, inherit `models.CachedModel`:

```python
class DeliveryCarrierZone(models.CachedModel):
    _name = 'delivery.carrier.zone'
    _description = 'Delivery Carrier Zone'

    _cached_data_fields = ('name', 'code', 'price')
    _cached_data_domain = [('active', '=', True)]

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    price = fields.Float()
```

Retrieve instances instantaneously from cache without database queries:
```python
zones = self.env['delivery.carrier.zone'].get_all()
```

---

## Database Aggregations (`_read_group`)

Always prefer `_read_group` over Python comprehensions for summaries:

```python
# Bad: Loads all records into memory to sum in Python
total = sum(self.env['sale.order.line'].search([('order_id', '=', order.id)]).mapped('price_subtotal'))

# Good: PostgreSQL SUM() in a single query
result = self.env['sale.order.line']._read_group(
    domain=[('order_id', '=', order.id)],
    aggregates=['price_subtotal:sum'],
)
total = result[0][0]
```

---

## Database Indexes (`models.Index`)

Declare database indexes for high-frequency filter and join fields:

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Composite index for search and sort
    _idx_partner_date = models.Index('(partner_id, date_order desc)')

    # Partial index for active records only (saves space and improves write speed)
    _idx_active_confirmation = models.Index(
        '(date_order) WHERE state = \'sale\''
    )
```

---

## Method Caching with `@api.ormcache`

```python
from odoo import api

@api.ormcache('company_id')
def _get_company_pricing_rules(self, company_id):
    # Executed once per company; cached in memory until invalidated
    return self.env['pricing.rule'].search([('company_id', '=', company_id)]).read(['name', 'multiplier'])
```

