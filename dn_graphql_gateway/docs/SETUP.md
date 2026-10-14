# GraphQL API Gateway for Odoo 19: Setup & Configuration Guide

## 1. Overview
`dn_graphql_gateway` is a production-ready, high-performance GraphQL API Gateway embedded natively within Odoo 19.
It provides a flexible query and mutation layer mirroring the standard [GraphQL specification](https://graphql.org/learn/), while running directly under the authenticated user's Odoo security context (`res.users`), enforcing Access Rights (`ir.model.access`), Record Rules (`ir.rule`), and multi-company segregation.

---

## 2. Prerequisites & Dependencies
- **Odoo Version**: Odoo 19.0+
- **Python**: 3.10+ (tested with Python 3.12)
- **Python Package**: `graphql-core` (version 3.2.0 or higher)

### Installing Python Dependency
Install `graphql-core` into your Odoo virtual environment:
```bash
/opt/venv312/bin/pip install graphql-core
```

---

## 3. Installation
1. Place the module into your custom addons directory:
   ```bash
   /opt/odoo19/dev/dn_graphql_gateway
   ```
2. Ensure your `/opt/odoo19.conf` includes the addons path:
   ```ini
   addons_path = /opt/odoo19/odoo/addons,/opt/odoo19/dev
   ```
3. Update the app list and install the module via CLI:
   ```bash
   /opt/odoo19/odoo-bin -c /opt/odoo19.conf -d <your_db> -i dn_graphql_gateway
   ```
   Or install it directly via **Apps** in the Odoo web client.

---

## 4. Architecture & Security Model

```
External Client (Frontend / Mobile / B2B)
       │
       ▼ Authorization: Bearer <api_key> (POST /graphql)
┌──────────────────────────────────────────────────────────┐
│ Odoo Controller (/graphql, auth='none', csrf=False)      │
├──────────────────────────────────────────────────────────┤
│ 1. Multipart check: Reject file uploads (415)            │
│ 2. Authenticate API Key: res.users.apikeys (scope='graphql')│
│ 3. Check expiration date & rate limit (429)              │
│ 4. request.update_env(user=service_user) [NO sudo()]     │
│ 5. Deny List AST Guard: Check global & key deny rules   │
│ 6. Savepoint Execution: Rollback ALL on any failure     │
│ 7. Write isolated audit log (dn.graphql.log)             │
└──────────────────────────────────────────────────────────┘
```

### Key Security Principles:
- **No `sudo()` Bypass**: All queries and mutations execute strictly in the authenticated service user's `env`. Odoo record rules automatically isolate customer or company data.
- **Service Users**: Each client or integration should be assigned a dedicated **Service User** (e.g. `API_Client_A`, `Mobile_App_User`) with minimal security groups.
- **Savepoint Atomicity**: All mutations in a single GraphQL request are wrapped in an atomic transaction savepoint. If any mutation field encounters a failure, the entire request rolls back cleanly.

---

## 5. Provisioning Service Users & API Keys

### Method A: Via Web UI (Recommended)
You can manage API keys and user permissions directly from the gateway menu:
1. Navigate to **GraphQL Gateway > API Keys**.
2. Click **New** to create a key profile:
   - **Key Description**: e.g., `Warehouse Mobile Scanner Integration`.
   - **Assigned User**: Select an existing user or create a dedicated service user.
   - **Expiration Date**: Optionally set a key validity deadline (e.g. 60 or 90 days).
3. Under the **User Permissions & Access Groups** tab, assign the desired security groups directly (e.g., `Inventory / User`, `Sales / Administrator`, `Purchase / User`).
4. Click **Generate API Key**:
   - The native cryptographic Bearer token (`res.users.apikeys`) is generated instantly.
   - The raw token is displayed in a secure highlight banner with a 1-click **Copy to Clipboard** button.
   - Save the key immediately (for security, it will not be shown again).

### Method B: Programmatic Key Generation (CLI / RPC / Python)
You can also generate keys via Python or XML-RPC:
```python
from datetime import datetime, timedelta

# Create API key valid for 90 days
user = env['res.users'].browse(user_id)
api_key = env['res.users.apikeys'].with_user(user).sudo()._generate(
    scope='graphql',
    name='Integration Client Key',
    expiration_date=datetime.utcnow() + timedelta(days=90)
)
print("Generated API Key:", api_key)
```

---

## 6. Configuring Model Whitelist (`dn.graphql.model`)
Only models explicitly registered in **GraphQL Gateway > Exposed Models** are exposed in the schema:

1. Navigate to **GraphQL Gateway > Exposed Models**.
2. Click **New** and select the model (e.g. `res.partner`, `sale.order`, `product.product`).
3. Configure permissions:
   - **Allow Query**: Enables connection query `res__partner` and `"res.partner"`.
   - **Allow Create Mutation**: Enables create mutation `"res.partner.create"`.
   - **Allow Update Mutation**: Enables update mutation `"res.partner.update"`.
   - **Allow Delete Mutation**: Enables delete mutation `"res.partner.delete"`.
   - **Default / Max Limit**: Set pagination safety thresholds (e.g., default 20, max 100).
4. *(Optional)* Select specific **Exposed Fields**. If left empty, all safe scalar fields are exposed automatically.

---

## 7. Configuring Blocklist Policies (`dn.graphql.deny`)
Use Deny Rules to enforce fine-grained restrictions:

1. Navigate to **GraphQL Gateway > Blocklist Policies**.
2. Click **New**.
3. Configure the rule:
   - **Target API Key**: Select a specific API key, or leave blank to enforce **Globally**.
   - **Odoo Model**: The restricted model (e.g. `ir.config_parameter`, `res.users`).
   - **Restricted Field**: (Optional) Specify a sensitive field (e.g. `password`, `email`).
   - **Restricted Operation**: `All`, `Read`, `Write`, `Create`, or `Delete`.
   - **Security Justification**: Reason recorded in audit logs.
4. **Deny Always Wins**: If a model or field is blocked, any request attempting to access it is rejected immediately with code `FORBIDDEN_RESOURCE` (HTTP 403).

---

## 8. Anti-Scraping & Performance Configuration
Navigate to **Settings > General Settings > GraphQL Gateway**:
- **Maximum Query Depth**: Set selection depth ceiling (default `6`). Queries exceeding this depth return HTTP 400.
- **Rate Limit (Per Minute)**: Set maximum requests per API key per minute (default `60`). Exceeding requests return HTTP 429 `RATE_LIMITED`.
- **Max Records per Query**: Hard ceiling on retrieved nodes across connections (default `1000`).

---

## 9. Inspecting Audit Logs (`dn.graphql.log`)
Every request is recorded via an **isolated database cursor**:
- Go to **GraphQL Gateway > Audit Logs**.
- Review client IP, executed user, status code, execution duration (ms), node count, and rollback status.
- Sensitive values (passwords, tokens, new API keys) are masked automatically (`***MASKED***`).
