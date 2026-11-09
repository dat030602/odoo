# Odoo 20 API Decorator Guide

## Coding Conventions

- Always use `@api.depends` for compute fields.
- Use `@api.ondelete` for delete validation instead of overriding `unlink()`.
- Always decorate `create()` with `@api.model_create_multi`.
- Use `@api.private` to block RPC invocation on public methods.
- Import `ormcache` directly from `odoo.api` (never `odoo.tools.cache`).
- Note: `@api.returns` is permanently removed.

---

## Table of Contents

- [Decorator Reference Summary](#decorator-reference-summary)
- [@api.depends](#apidepends)
- [@api.constrains](#apiconstrains)
- [@api.ondelete](#apiondelete)
- [@api.model_create_multi](#apimodel_create_multi)
- [@api.private](#apiprivate)
- [@api.readonly](#apireadonly)
- [@api.ormcache](#apiormcache)
- [@api.onchange](#apionchange)

---

## Decorator Reference Summary

| Decorator | Target | Purpose |
|-----------|--------|---------|
| `@api.depends(*args)` | Method | Declares field dependencies for computed fields |
| `@api.depends_context(*args)` | Method | Context keys triggering recomputation |
| `@api.constrains(*args)` | Method | Validates data consistency before commit |
| `@api.ondelete(at_uninstall=...)` | Method | Prevents record deletion if conditions aren't met |
| `@api.model_create_multi` | `create()` | Handles batch creation of records (`vals_list`) |
| `@api.private` | Method | Blocks RPC / API invocation on public methods |
| `@api.readonly` | Method | Read-only execution mode (replica routing) |
| `@api.ormcache(*params)` | Method | In-memory method result caching |
| `@api.onchange(*args)` | Method | Live UI interactive calculations |

---

## @api.depends

```python
subtotal = fields.Monetary(compute='_compute_subtotal', store=True)

@api.depends('price_unit', 'quantity', 'discount')
def _compute_subtotal(self):
    for line in self:
        line.subtotal = line.quantity * line.price_unit * (1 - (line.discount or 0.0) / 100.0)
```

---

## @api.constrains

```python
from odoo.exceptions import ValidationError

@api.constrains('date_start', 'date_end')
def _check_dates(self):
    for record in self:
        if record.date_start and record.date_end and record.date_start > record.date_end:
            raise ValidationError("Start Date cannot be later than End Date!")
```

---

## @api.ondelete

```python
from odoo.exceptions import UserError

@api.ondelete(at_uninstall=False)
def _unlink_except_confirmed(self):
    if any(record.state == 'confirmed' for record in self):
        raise UserError("You cannot delete a confirmed record!")
```

---

## @api.model_create_multi

```python
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if not vals.get('code'):
            vals['code'] = self.env['ir.sequence'].next_by_code('my.model.seq')
    return super().create(vals_list)
```

---

## @api.private

Marks public method names as unreachable from external JSON-RPC / XML-RPC calls:

```python
@api.private
def internal_system_sync(self):
    """Cannot be invoked externally over the web API."""
    ...
```

---

## @api.readonly

Marks methods that perform read-only actions, allowing database optimizations:

```python
@api.readonly
def get_user_statistics(self):
    return {
        'total_orders': self.search_count([('user_id', '=', self.env.uid)]),
    }
```

---

## @api.ormcache

Import directly from `odoo.api`:

```python
from odoo import api

@api.ormcache('partner_id', 'currency_id')
def _get_partner_discount_rate(self, partner_id, currency_id):
    # Expensive query or calculation
    return self._calculate_discount(partner_id, currency_id)
```

