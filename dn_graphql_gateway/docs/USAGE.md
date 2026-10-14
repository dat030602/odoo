# GraphQL API Gateway: Developer Usage Guide

Welcome to the **GraphQL API Gateway for Odoo 19**. This gateway provides an expressive, client-driven GraphQL interface over Odoo models with native ACL, Record Rules, atomic transaction rollbacks, and enterprise security guardrails.

---

## 1. Gateway Endpoint & Authentication

### HTTP Endpoint
- **URL**: `POST https://<your-odoo-domain>/graphql`
- **Interactive Docs**: `GET https://<your-odoo-domain>/graphql/docs`
- **Content-Type**: `application/json` *(File uploads / multipart are strictly forbidden)*

### Authentication Header
Every request must include a Bearer API Key generated with scope `graphql`:
```http
Authorization: Bearer <your_api_key_token>
```

---

## 2. Model Syntax: Quoted vs Standard

The gateway natively supports both **exact quoted Odoo model names** and **standard GraphQL identifiers**:

| Operation | Quoted Odoo Syntax (Recommended) | Standard GraphQL Identifier Syntax |
| :--- | :--- | :--- |
| **Query Connection** | `"res.partner"(first: 10)` | `res__partner(first: 10)` |
| **Create Mutation** | `"res.partner.create"(values: {...})` | `res__partner__create(values: {...})` |
| **Update Mutation** | `"res.partner.update"(id: 1, values: {...})` | `res__partner__update(id: 1, values: {...})` |
| **Delete Mutation** | `"res.partner.delete"(id: 1)` | `res__partner__delete(id: 1)` |

---

## 3. Querying Data

### 3.1 Basic Pagination (Relay-Style Connection)
Queries follow the GraphQL Connection specification (`totalCount`, `pageInfo`, `edges`, `node`):

```graphql
query GetPartners {
  "res.partner"(first: 10, order: "id desc") {
    totalCount
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    edges {
      cursor
      node {
        id
        name
        email
        phone
        active
      }
    }
  }
}
```

### 3.2 Filtering with Odoo Domains
Use the `domain` argument to pass standard Odoo domain expressions:

```graphql
query GetCompanies {
  "res.partner"(
    first: 20
    domain: "[('is_company', '=', True), ('customer_rank', '>', 0)]"
    order: "name asc"
  ) {
    totalCount
    edges {
      node {
        id
        name
        email
        commercial_company_name
      }
    }
  }
}
```

### 3.3 Lookup by ID or List of IDs
```graphql
query GetSpecificPartners {
  # Single record lookup
  single: "res.partner"(id: 42) {
    edges {
      node {
        id
        name
      }
    }
  }

  # Multi-ID lookup
  batch: "res.partner"(ids: [10, 11, 12]) {
    edges {
      node {
        id
        name
      }
    }
  }
}
```

### 3.4 Traversing Relationships (Many2one)
```graphql
query GetPartnersWithCompany {
  "res.partner"(first: 5) {
    edges {
      node {
        id
        name
        company_id {
          id
          name
        }
        country_id {
          id
          name
          code
        }
      }
    }
  }
}
```

---

## 4. Mutating Data (Create, Update, Delete)

### 4.1 Creating a Record
```graphql
mutation CreatePartner {
  "res.partner.create"(
    values: {
      name: "Acme Logistics International"
      email: "contact@acme.com"
      phone: "+1-555-0199"
      is_company: true
    }
  ) {
    node {
      id
      name
      email
    }
    userErrors {
      message
      field
      code
    }
  }
}
```

### 4.2 Updating a Record
```graphql
mutation UpdatePartner {
  "res.partner.update"(
    id: 154
    values: {
      email: "billing@acme.com"
      phone: "+1-555-0200"
    }
  ) {
    node {
      id
      name
      email
      phone
    }
    userErrors {
      message
      field
      code
    }
  }
}
```

### 4.3 Deleting a Record
```graphql
mutation DeletePartner {
  "res.partner.delete"(id: 154) {
    success
    id
    userErrors {
      message
      field
      code
    }
  }
}
```

### 4.4 Invoking Business Methods (Workflow Actions)
You can trigger public Odoo workflow and business methods (e.g. `action_confirm`, `button_validate`, `action_cancel`, `action_assign`) on any whitelisted model:

#### Pattern A: Model-Specific Quoted Syntax (`"<model>.call"`)
```graphql
mutation ConfirmSaleOrder {
  "sale.order.call"(id: 42, method: "action_confirm") {
    success
    result
    userErrors {
      message
      field
      code
    }
  }
}
```

#### Pattern B: Multi-Record Execution with Arguments
```graphql
mutation AssignPickings {
  "stock.picking.call"(ids: [101, 102], method: "action_assign", kwargs: "{}") {
    success
    result
    userErrors {
      message
    }
  }
}
```

#### Pattern C: Dynamic Generic Syntax (`callMethod`)
```graphql
mutation ConfirmPurchaseOrder {
  callMethod(model: "purchase.order", id: 18, method: "button_confirm") {
    success
    result
    userErrors {
      message
    }
  }
}
```
> [!IMPORTANT]
> - **Private Methods Protected**: Calling internal methods starting with `_` (e.g. `_write`, `_compute_password`) is strictly forbidden and rejected immediately.
> - **Permissions Respected**: Business actions run under the authenticated service user's context, adhering strictly to Odoo ACL and Record Rules.
> - **Atomic Savepoint**: If the business action raises an exception (e.g., `UserError("Inventory not available")`), it is returned in `userErrors` and the transaction is cleanly rolled back.

### 4.5 Reporting & Deep Relational Queries (High-Volume Big Data)

The gateway supports deep nested Many2one navigation, One2many collections, and high-volume batch queries optimized with Odoo ORM prefetching.

#### Pattern A: Inventory Movement Report with Deep Locations (`stock.picking.picking_type_id.location_src_id.name`)
```graphql
query InventoryMovementReport($limit: Int) {
  "stock.picking"(first: $limit, order: "id desc") {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        name
        state
        scheduled_date
        picking_type_id {
          id
          name
          code
          location_src_id {
            id
            name
          }
        }
        location_id {
          id
          name
        }
        location_dest_id {
          id
          name
        }
        move_ids {
          id
          product_id {
            display_name
          }
          product_uom_qty
          quantity
        }
      }
    }
  }
}
```

#### Pattern B: Sales Report by Customer (Detailed Breakdown with Order Lines)
```graphql
query SalesReportByCustomer($limit: Int, $domain: String) {
  "sale.order"(first: $limit, domain: $domain, order: "date_order desc") {
    totalCount
    edges {
      node {
        id
        name
        date_order
        state
        partner_id {
          id
          name
          email
          phone
        }
        amount_untaxed
        amount_tax
        amount_total
        order_line {
          id
          name
          product_uom_qty
          price_unit
          price_subtotal
        }
      }
    }
  }
}
```

#### Benchmark Results (Native Odoo 19 + GraphQL Gateway)
| Entity | Batch Size | Response Size | Execution Time | Latency / Record |
|---|---|---|---|---|
| `stock.picking` (with deep location & moves) | **100 records** | 23.4 KB | **37.7 ms** | 0.37 ms |
| `stock.picking` (with deep location & moves) | **500 records** | 117.2 KB | **62.9 ms** | 0.12 ms |
| `stock.picking` (with deep location & moves) | **1,000 records** | 234.8 KB | **177.4 ms** | 0.17 ms |
| `sale.order` (with lines & customer) | **100 orders** | 26.0 KB | **42.7 ms** | 0.42 ms |
| `sale.order` (with lines & customer) | **500 orders** | 135.8 KB | **77.4 ms** | 0.15 ms |

*Zero N+1 query latency: Odoo ORM prefetching batches all related records across the recordset.*

---

## 5. Atomic Savepoint Rollback Behavior

In enterprise manufacturing and financial systems, partial success in multi-step operations leads to inconsistent data. **The GraphQL Gateway guarantees full atomic transaction rollback**:

- When multiple mutations are included in a single request:
  - If **ANY** mutation encounters an error (Odoo `ValidationError`, `UserError`, `AccessError`, or `userErrors`), **ALL previous mutations in that request are rolled back** via a PostgreSQL transaction savepoint.
  - The database remains completely unchanged.
  - The response returns `extensions: { "rolledBack": true }`.

### Example: Multi-step Mutation with Rollback
```graphql
mutation CreateBulkEntities {
  step1: "res.partner.create"(values: { name: "Valid Entity" }) {
    node { id name }
    userErrors { message }
  }
  step2: "res.partner.update"(id: 9999999, values: { name: "Non-existent Record" }) {
    node { id }
    userErrors { message code }
  }
}
```
**Response:**
```json
{
  "data": {
    "res.partner.create": { "node": null, "userErrors": [] },
    "res.partner.update": {
      "node": null,
      "userErrors": [{ "message": "Record ID 9999999 not found on res.partner.", "code": "NOT_FOUND" }]
    }
  },
  "extensions": {
    "rolledBack": true,
    "requestId": "9c12b704-5829-43c2-bf72-88741369c9b1"
  }
}
```
*Note: `Valid Entity` is completely undone in the database.*

---

## 6. API Key Expiration & In-place Rotation

To prevent stale or compromised API keys, clients can rotate their key in-place:

```graphql
mutation RotateCredentials {
  rotateApiKey(expiresInDays: 60) {
    newKey
    expirationDate
    userErrors {
      message
      code
    }
  }
}
```

**Response:**
```json
{
  "data": {
    "rotateApiKey": {
      "newKey": "7f09c81b2a43...",
      "expirationDate": "2026-12-09T03:25:00",
      "userErrors": []
    }
  }
}
```
- **New Key**: Returned **only once**. Save it securely.
- **Old Key**: Revoked immediately.
- **Audit Logs**: The new key is automatically masked in logs (`***MASKED***`).

---

## 7. Error Handling & Status Codes

All errors adhere to standard GraphQL error structures:

```json
{
  "data": null,
  "errors": [
    {
      "message": "Access to field 'password' on model 'res.users' is forbidden.",
      "extensions": {
        "code": "FORBIDDEN_RESOURCE",
        "requestId": "3f44e8dc-7212-4043-a60d-7db043be89c1"
      }
    }
  ]
}
```

| HTTP Status | Error Code | Trigger Condition |
| :---: | :--- | :--- |
| **401** | `UNAUTHENTICATED` | Missing or invalid Bearer token. |
| **401** | `KEY_EXPIRED` | API key has exceeded its expiration date. |
| **403** | `FORBIDDEN_RESOURCE` | Attempting to access a model/field blocked by a Deny Policy. |
| **403** | `FORBIDDEN` | Odoo ACL or Record Rule permission denied. |
| **400** | `BAD_USER_INPUT` | Odoo `ValidationError` or constraint violation. |
| **400** | `GRAPHQL_VALIDATION_FAILED` | Query syntax error or exceeding maximum depth (default 6). |
| **415** | `UPLOAD_NOT_ALLOWED` | Multipart/form-data upload attempted. |
| **429** | `RATE_LIMITED` | Exceeded per-minute request rate limit. |
| **500** | `INTERNAL_SERVER_ERROR` | Unhandled server exception (traceback masked). |

---

## 8. Code Examples

### 8.1 cURL
```bash
curl -X POST https://your-odoo.com/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GRAPHQL_API_KEY" \
  -d '{
    "query": "query { \"res.partner\"(first: 3) { edges { node { id name email } } } }"
  }'
```

### 8.2 Python (requests)
```python
import requests

url = "https://your-odoo.com/graphql"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_GRAPHQL_API_KEY",
}
payload = {
    "query": """
    query GetPartners($limit: Int!) {
        "res.partner"(first: $limit) {
            totalCount
            edges {
                node {
                    id
                    name
                    email
                }
            }
        }
    }
    """,
    "variables": {"limit": 5}
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### 8.3 JavaScript / Node.js (fetch)
```javascript
const response = await fetch("https://your-odoo.com/graphql", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_GRAPHQL_API_KEY",
  },
  body: JSON.stringify({
    query: `
      query {
        "res.partner"(first: 5) {
          edges {
            node {
              id
              name
            }
          }
        }
      }
    `,
  }),
});

const result = await response.json();
console.log(result.data["res.partner"]);
```
