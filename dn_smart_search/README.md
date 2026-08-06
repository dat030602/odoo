# Smart Search

**Global cross-model search from a single search box.**

Search records across multiple Odoo models (Sale Orders, Purchases, Invoices,
Contacts, Tasks, Products, Transfers, ...) from one keyboard-friendly search box
in the systray. Results are ranked by a smart scoring algorithm, highlighted,
grouped by model, and opened instantly — without leaving your current screen.

| Field        | Value                          |
|--------------|--------------------------------|
| Author       | Dat Nguyen                     |
| Website      | https://www.datnguyen.dev      |
| Category     | Tools                          |
| Version      | 19.0.1.0.0                     |
| License      | OPL-1                          |
| Compatibility| Odoo 19 (depends on `web`)     |

---

## Features

- **Global cross-model search** — a single search box queries every enabled model.
- **Smart scoring** — results are ranked by relevance with keyword-based boosts
  (emails/phones &rarr; Contacts, `SO`/`PO`/`INV`/`wh/...` prefixes &rarr; matching orders/invoices/transfers).
- **Query highlighting** — matching terms are highlighted in the results.
- **Keyboard navigation** — `Ctrl+K` opens the search, `Arrow` keys navigate,
  `Enter` opens the selected record, `Escape` closes.
- **Configurable providers** — choose which models are searchable, which fields
  are indexed, the subtitle field, the priority and the icon.
- **No-config startup** — sensible default configurations are created
  automatically by a post-install hook.
- **Lightweight & fast** — in-memory caching (30s TTL) and result de-duplication
  keep the UI responsive.
- **Clean integration** — an OWL systray component; no visible change until
  activated.

---

## How it works (workflow)

1. The user opens the search with **`Ctrl+K`** (or clicks the systray button).
2. As the user types, the OWL `SmartSearchDialog` calls the JSON route
   **`/smart/search`** (`controllers/main.py`).
3. The route delegates to **`smart.search`** (`models/smart_search.py`), which
   iterates over every model flagged with **`_smart_search_provider = True`**.
4. The generic provider
   (**`smart.search.provider.generic`**) reads the active
   **`smart.search.config`** records, builds an `ilike` domain on the configured
   fields, executes the search and scores each record.
5. Results are **de-duplicated**, **sorted by score**, **cached**, and returned to
   the client where they are **highlighted** and displayed grouped by model.
6. Picking a result opens the record form in the current tab.

```
User types (Ctrl+K) -> /smart/search JSON -> smart.search.search()
        -> smart.search.provider.generic.search() -> smart.search.config
        -> model.search(domain) -> score -> dedup -> sort -> cache -> highlight
```

---

## Configuration

Manage searchable models from **Settings > Smart Search**
(menu placed under *Administration*, access limited to *System Administrator*).

Each `smart.search.config` record controls one model:

| Field                | Description                                              |
|----------------------|----------------------------------------------------------|
| Name                 | Human-readable label.                                    |
| Model                | The `ir.model` to search.                                |
| Active               | Enable/disable the model.                                |
| Priority             | Order in which models are evaluated (default `100`).     |
| Search fields        | Comma-separated field names used for the `ilike` search. |
| Subtitle field       | Field shown as subtitle in results.                      |
| Icon                 | Font Awesome icon class displayed next to results.       |

### Default providers (created by `post_init_hook`)

| Model           | Label           | Search fields                              | Subtitle      | Icon               |
|-----------------|-----------------|--------------------------------------------|---------------|--------------------|
| `sale.order`    | Sale Orders     | `name,client_order_ref,partner_id`         | `partner_id`  | `fa-shopping-cart` |
| `purchase.order`| Purchase Orders | `name,partner_ref,partner_id`              | `partner_id`  | `fa-shopping-basket` |
| `account.move`  | Invoices        | `name,ref,invoice_origin`                  | `partner_id`  | `fa-file-text-o`   |
| `res.partner`   | Contacts        | `name,email,phone,mobile,ref`              | `email`       | `fa-user`          |
| `stock.picking` | Transfers       | `name,origin,partner_id`                   | `partner_id`  | `fa-truck`         |
| `project.task`  | Tasks           | `name,description,partner_id`              | `partner_id`  | `fa-tasks`         |
| `product.product`| Products       | `default_code,name,barcode`                | `default_code`| `fa-cube`          |

---

## Usage

1. **Open the search** — press `Ctrl+K` anywhere, or click the *🔍 Search everything*
   systray entry.
2. **Type a keyword** — e.g. `SO0012`, `0123456789`, an email, or a product name.
3. **Navigate** — use `Arrow Up` / `Arrow Down` (or hover) to move the highlight.
4. **Open** — press `Enter` or click a result to open its form view.
5. **Close** — press `Escape` or click outside.

Results are grouped by model, ranked by score, and matching keywords are
highlighted in bold.

---

## Technical details

### Models

| Model                                | Type      | Description                                             |
|--------------------------------------|-----------|---------------------------------------------------------|
| `smart.search`                       | Abstract  | Entry point with query caching & de-duplication.        |
| `smart.search.config`                | Record    | Per-model search configuration (CRUD + clear cache).   |
| `smart.search.provider`              | Abstract  | Base provider contract (`search(keyword, limit)`).      |
| `smart.search.provider.generic`      | Abstract  | Default implementation reading `smart.search.config`.   |
| `ir.model`                           | (inherit) | Helpers returning default icons & fields per model.     |

### Scoring algorithm (`_score_record` / `_keyword_boost`)

- **Exact** match of the (normalized) keyword in any candidate field -> 100.
- **Starts-with** match -> 90.
- **Contains** match -> 70.
- Otherwise a `difflib.SequenceMatcher` ratio (x60) fallback.
- Boosters: emails/phones +30 for contacts; `SO0012`, `PO0012`, `INV0012` and
  `wh/...` transfer prefixes get +35 on their respective models; names with a
  space get +10 for contacts/tasks.

### Caching

- 30-second TTL keyed by `(uid, company, keyword, limit)`.
- Max 256 entries with LRU-style pruning on insert.
- Cache invalidated automatically on create/write/unlink of `smart.search.config`.

### Assets

- `static/src/js/smart_search.js` — OWL systray button + modal dialog
  (`SmartSearchSystray`, `SmartSearchDialog`).
- `static/src/xml/smart_search.xml` — QWeb templates for both components.
- Registered under `web.assets_backend`.

---

## Installation

1. Copy the `dn_smart_search` folder into your Odoo `addons` path.
2. Update the apps list and install **Smart Search** (no manual setup needed).
3. (Optional) Tweak providers under *Settings > Smart Search*.

---

## License

This module is distributed under the **OPL-1** (Odoo Proprietary License) license.
See the `LICENSE` file if present.
