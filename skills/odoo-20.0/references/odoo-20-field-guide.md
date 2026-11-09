# Odoo 20 Field Guide

## Coding Conventions

- Keep fields and their compute, inverse, search, and `compute_sql` methods together.
- Use `compute_sql` on computed fields whenever SQL-level querying, filtering, or sorting is required without storing the field in the database.
- Always provide an explicit `compute_sudo` parameter when declaring `compute_sql`.
- Use `init_storage` on field definitions for initial data population instead of overriding `_init_column`.
- Use `aggregator=` for list/graph/pivot view aggregations (never `group_operator=`).
- Store computed fields only when strictly necessary (e.g. required for foreign key indexes or high-frequency join criteria).

---

## Table of Contents

- [Field Types](#field-types)
- [Basic Fields](#basic-fields)
- [Numeric & Monetary Fields](#numeric--monetary-fields)
- [Relational Fields](#relational-fields)
- [Computed Fields & `compute_sql`](#computed-fields--compute_sql)
- [Field Initialization with `init_storage`](#field-initialization-with-init_storage)
- [Field Parameters Reference](#field-parameters-reference)

---

## Field Types

| Category | Types |
|----------|-------|
| **Basic** | `Boolean`, `Char`, `Text`, `Html` |
| **Numeric** | `Integer`, `Float`, `Monetary` |
| **Date/Time** | `Date`, `Datetime` |
| **Relational** | `Many2one`, `One2many`, `Many2many` |
| **Selection & Reference** | `Selection`, `Reference`, `Many2oneReference` |
| **Binary & Media** | `Binary`, `Image` |
| **Structured Data** | `Json`, `Properties`, `PropertiesDefinition` |

---

## Basic Fields

### Boolean
```python
active = fields.Boolean(string="Active", default=True)
is_company = fields.Boolean(string="Is a Company")
```

### Char & Text
```python
name = fields.Char(string="Name", required=True, translate=True)
code = fields.Char(string="Reference Code", size=20)
description = fields.Text(string="Internal Notes")
website_description = fields.Html(string="Public Description", sanitize_style=True)
```

### Selection
```python
state = fields.Selection(
    selection=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ],
    string="Status",
    default='draft',
    required=True,
    copy=False,
    tracking=True,
)
```

---

## Numeric & Monetary Fields

### Integer & Float
```python
sequence = fields.Integer(string="Sequence", default=10)
discount = fields.Float(string="Discount (%)", digits='Discount', aggregator='avg')
```

### Monetary
Requires `currency_field` (defaults to `'currency_id'`).
```python
currency_id = fields.Many2one('res.currency', string="Currency", required=True)
amount_untaxed = fields.Monetary(
    string="Untaxed Amount",
    currency_field='currency_id',
    aggregator='sum',
)
```

---

## Binary & Image Fields

In Odoo 20, binary values are wrapped in `BinaryValue` objects providing `.filename`, `.content`, `.size`, and `.mimetype`:

```python
document = fields.Binary(string="Attachment Document", attachment=True)
document_filename = fields.Char(string="File Name")
image_1920 = fields.Image(string="Product Image", max_width=1920, max_height=1920)
```

### Reading Binary Fields: `load='web'` vs legacy `bin_size`
- `bin_size` has been **completely removed** from the ORM.
- To read file metadata (such as size and filename) without loading the full base64 payload into memory, pass `load='web'`:
  ```python
  # Returns {'size': 20480, 'filename': 'spec.pdf'}
  data = self.read(['document'], load='web')
  ```
- Normal RPC reads return a dictionary: `{'filename': ..., 'content': ..., 'size': ...}`.

---

## Relational Fields

### Many2one
```python
partner_id = fields.Many2one(
    comodel_name='res.partner',
    string="Customer",
    required=True,
    ondelete='restrict',
    index=True,
    check_company=True,
)
```

### One2many
```python
order_line_ids = fields.One2many(
    comodel_name='sale.order.line',
    inverse_name='order_id',
    string="Order Lines",
    copy=True,
)
```

### Many2many
```python
tag_ids = fields.Many2many(
    comodel_name='project.tags',
    relation='project_task_tag_rel',
    column1='task_id',
    column2='tag_id',
    string="Tags",
)
```

---

## Computed Fields & `compute_sql`

### Standard Computed Fields
```python
total_qty = fields.Float(
    string="Total Quantity",
    compute='_compute_total_qty',
    store=True,
)

@api.depends('order_line_ids.product_uom_qty')
def _compute_total_qty(self):
    for order in self:
        order.total_qty = sum(order.order_line_ids.mapped('product_uom_qty'))
```

### Direct SQL Computed Fields (`compute_sql`)

`compute_sql` allows computed fields to be queried, filtered, and aggregated in SQL **without storing them in the database table**:

```python
from odoo import api, fields, models
from odoo.tools import SQL

class SaleOrder(models.Model):
    _name = 'sale.order'

    has_discounted_lines = fields.Boolean(
        string="Has Discounted Lines",
        compute='_compute_has_discounted_lines',
        compute_sql='_compute_sql_has_discounted_lines',
        compute_sudo=True,  # Explicit compute_sudo is required when compute_sql is set
    )

    @api.depends('order_line_ids.discount')
    def _compute_has_discounted_lines(self):
        for order in self:
            order.has_discounted_lines = any(l.discount > 0 for l in order.order_line_ids)

    def _compute_sql_has_discounted_lines(self, table):
        """Produce SQL expression representing this field."""
        return SQL(
            """EXISTS (
                SELECT 1 FROM sale_order_line sol
                WHERE sol.order_id = %s AND sol.discount > 0
            )""",
            table.id,
        )
```

Benefits:
- Can be searched: `self.env['sale.order'].search([('has_discounted_lines', '=', True)])` runs entirely in PostgreSQL via the generated SQL subquery!
- No database column required, saving disk space and avoiding table write overhead.

---

## Field Initialization with `init_storage`

In Odoo 20, use `init_storage` on the field definition to initialize new columns on existing database rows:

```python
class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_rank_score = fields.Integer(
        string="Customer Rank Score",
        init_storage='_init_customer_rank_score',
    )

    def _init_customer_rank_score(self):
        self.env.cr.execute(
            SQL("UPDATE res_partner SET customer_rank_score = 100 WHERE customer_rank > 0")
        )
```

> **Odoo 20 Note**: `_init_column(column_name)` is deprecated in favor of `Field.init_storage`.

---

## Field Parameters Reference

| Parameter | Type | Description |
|-----------|------|-------------|
| `string` | str | User-facing field label |
| `help` | str | Tooltip documentation |
| `required` | bool | Enforces NOT NULL at database and ORM levels |
| `readonly` | bool | User cannot modify the field via UI |
| `copy` | bool | Included when duplicating a record via `copy()` (defaults to `False` for `compute` and `state`) |
| `store` | bool | Stored in PostgreSQL table (default `True` for basic, `False` for compute) |
| `compute` | str/callable | Python compute method |
| `compute_sql` | str/callable | SQL generator method for direct SQL queries |
| `compute_sudo` | bool | Computes field in superuser mode |
| `precompute` | bool | Computes field before database record insertion |
| `inverse` | str/callable | Method to save changes from computed field back to source |
| `search` | str/callable | Custom domain generator for non-stored fields |
| `aggregator` | str | Operator for view aggregations (`'sum'`, `'avg'`, `'min'`, `'max'`, `'bool_and'`, `'bool_or'`, `'recordset'`) |
| `init_storage` | str/callable | Storage initialization callback on schema creation |
| `company_dependent` | bool | Multi-company jsonb property field |
| `tracking` | bool/int | Logs changes in chatter |

