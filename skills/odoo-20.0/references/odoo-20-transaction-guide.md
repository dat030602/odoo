# Odoo 20 Database Transactions Guide

## Coding Conventions

- Wrap external API calls and fragile operations in `with self.env.cr.savepoint():`.
- After catching exceptions inside a savepoint, call `self.env.transaction.clear()` or `self.env.transaction.reset()`.
- Invalidate caches via `self.env.transaction.invalidate_ormcache()` (never `registry.clear_cache()`).
- Always `flush_all()` before running raw SQL that depends on pending ORM writes.

---

## Table of Contents

- [Transaction Life Cycle](#transaction-life-cycle)
- [Savepoints & Error Recovery](#savepoints--error-recovery)
- [Cache Invalidation & Reset](#cache-invalidation--reset)
- [Handling Concurrency & Serialization](#handling-concurrency--serialization)
- [Flushing Pending ORM Operations](#flushing-pending-orm-operations)

---

## Transaction Life Cycle

Each HTTP or RPC request in Odoo runs within an isolated PostgreSQL transaction:
1. An environment cursor `cr` and `transaction` object are initialized.
2. ORM operations write data into memory and flush to PostgreSQL when necessary.
3. At the end of the request, `cr.commit()` commits changes. If an unhandled exception occurs, `cr.rollback()` discards changes.

---

## Savepoints & Error Recovery

To isolate errors and prevent an entire transaction from aborting, use savepoints:

```python
for order in orders:
    try:
        with self.env.cr.savepoint():
            order.action_confirm_payment()
    except Exception as e:
        _logger.error("Failed to process payment for order %s: %s", order.name, e)
        # Reset transaction internal structures safely:
        self.env.transaction.clear()
```

---

## Cache Invalidation & Reset

> **Odoo 20 Update**: `self.env.clear()` and `registry.clear_cache()` are replaced by transaction methods:

```python
# Clear dirty cache and recompute buffers
self.env.transaction.clear()

# Reset transaction state
self.env.transaction.reset()

# Invalidate ormcache
self.env.transaction.invalidate_ormcache()

# Invalidate security access rules cache
self.env.invalidate_access_cache()
```

---

## Handling Concurrency & Serialization

When updating shared records (such as stock quantities or sequence counters), handle concurrency conflicts gracefully:

```python
from psycopg2.errors import SerializationFailure

try:
    with self.env.cr.savepoint():
        self.env.cr.execute(
            SQL("SELECT id FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", quant.id)
        )
        quant.write({'quantity': quant.quantity - 1})
except SerializationFailure:
    _logger.warning("Quant is locked by concurrent transaction, retrying...")
```

---

## Flushing Pending ORM Operations

Because Odoo delays writing changes to PostgreSQL until necessary, always flush pending writes before running direct SQL queries:

```python
# Ensure all pending ORM writes are sent to PostgreSQL
self.env.flush_all()

# Direct SQL query now sees up-to-date data
self.env.cr.execute(SQL("SELECT sum(amount_total) FROM sale_order WHERE state = 'sale'"))
```

