# Odoo 19 Universal REST Connector & Inbound Gateway: Administrator & Setup Guide

**Module:** `dn_connector_base`  
**Target Platform:** Odoo 19.0 (Community & Enterprise), Python 3.12  
**Target Audience:** System Administrators, DevOps Engineers, Solution Architects, and Functional Operators  
**Document Version:** 2.2.0  

---

## 1. Executive Summary & Architecture

The `dn_connector_base` module establishes an enterprise-grade integration foundation for Odoo 19. Operating on the core architectural design philosophy **"Raw Data First, Business Later"**, the module cleanly decouples high-speed data reception, network transport, protocol authentication, and concurrency queuing from business-specific ORM operations.

![Universal Inbound Gateway & Concurrency Engine Architecture](/dn_connector_base/static/description/architecture_flow.svg)

*Figure 1.1: Universal Inbound Gateway Architecture — From Nginx edge rate limiting and sub-50ms HTTP fast acknowledgment to PostgreSQL `SKIP LOCKED` batch processing and Dead Letter Queue isolation.*

### 1.1 High-Throughput Ingestion vs. Registry Freeze

Traditional Odoo integration modules frequently expose HTTP controllers that directly parse payloads, instantiate ORM models (`sale.order`, `res.partner`), and compute business logic inside the live HTTP request thread. This pattern suffers from severe production bottlenecks:
1. **Thread Starvation:** Synchronous ORM operations hold open HTTP worker threads for seconds or minutes. Under sudden traffic spikes (e.g., flash sales, Black Friday webhooks), all Odoo HTTP workers become exhausted, rendering the user interface inaccessible to internal operators.
2. **Registry Freeze & Table Locks:** Complex business logic locks related tables (`stock.quant`, `account.move`), triggering lock contention and cascading serialization failures across the ERP.
3. **Data Loss on Failure:** If an exception occurs (e.g., validation error, concurrency collision, missing tax configuration), the HTTP request crashes with HTTP 500. Unless the external platform reliably retries, the webhook payload is permanently lost.

**The `dn_connector_base` Solution:**
- **Zero-Code Ingestion:** Inbound webhooks are captured by a lightweight controller (`/connector/in/<token>`) running outside user session contexts (`save_session=False`, `csrf=False`).
- **Sub-50ms Response Times:** The gateway verifies security (IP allowlists, HMAC cryptography), saves the raw event to the transactional inbox (`connector.inbound.message`), and immediately replies with HTTP 202 (`{"status": "queued", "uuid": "..."}`).
- **Zero Registry Freeze:** Business transformation occurs asynchronously in background cron workers. The web-facing HTTP threads are instantly released.
- **Resilient Dead Letter Queue (DLQ):** Messages that fail execution are retried automatically using exponential backoff with randomized jitter. If errors persist beyond maximum retry attempts, payloads are quarantined in the Dead Letter Queue for operator inspection, eliminating data loss.

### 1.2 Technical Specifications & System Limits Matrix

| Parameter | Default Value | Configurable Location | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **Max Payload Size** | `10 MB` | Hardcoded Guard in `controllers/main.py` | Returns HTTP 413 (`Payload Too Large`) |
| **Circuit Breaker Threshold** | `10,000 messages` | `connector.inbound.endpoint.max_backlog` | Returns HTTP 429 (`Retry-After: 30`) |
| **Worker Batch Size** | `100 messages` | `res.config.settings` (`connector_default_batch_size`) | `LIMIT` clause in cron SQL query |
| **Concurrency Locking** | Row-level | Background cron processor | PostgreSQL `FOR UPDATE SKIP LOCKED` |
| **Max Retry Attempts** | `5 attempts` | `connector.inbound.message.max_attempts` | Transitions to `dead` state upon exhaustion |
| **Initial Retry Delay** | `10 seconds` | Processor formula | Formula: `min(3600, 10 * 2^attempts) + jitter` |
| **Completed Retention** | `30 days` | `res.config.settings` (`connector_retention_days_done`) | Daily purge cron (`chunk=5000`) |
| **Dead Letter Retention**| `90 days` | `res.config.settings` (`connector_retention_days_dead`) | Daily purge cron (`chunk=5000`) |
| **Lock Contention Timeout**| `60 seconds` | `res.config.settings` (`connector_lock_timeout`) | Transaction execution deadline |

---

## 2. Installation & Pre-Configuration Requirements

### 2.1 Dependencies & Module Installation

The `dn_connector_base` module depends exclusively on Odoo core components:
- `base` (Odoo framework primitives, ORM, security)
- `web` (User interface assets, form and list view components)
- `mail` (Chatter tracking and activity mixins on endpoints)

To install or upgrade the module from the terminal using environment settings:
```bash
# Source environment variables
source /opt/odoo19/.agents/.env

# Upgrade or install module
$ODOO_PYTHON $ODOO_BIN -c $ODOO_CONF -d $ODOO_DB -u dn_connector_base --stop-after-init
```

> [!IMPORTANT]
> Always verify that your Python runtime includes cryptographic and networking libraries: `hashlib`, `hmac`, `ipaddress`, and `psycopg2`. These are standard in Python 3.12 installations on Linux.

### 2.2 System Base URL Configuration (`web.base.url`)

The Inbound Gateway automatically computes public webhook URLs using the system parameter `web.base.url`. If this parameter is set to `http://localhost:8019`, generated webhook URLs will not be accessible to external services.

1. Navigate to **Settings -> Technical -> Parameters -> System Parameters** (Activate Developer Mode).
2. Locate the key `web.base.url`.
3. Set the value to your publicly accessible, HTTPS-secured domain (e.g., `https://odoo.yourcompany.com`).
4. **Freeze Automatic Overwrites:** Create or update the boolean parameter `web.base.url.freeze` with value `True` to prevent Odoo from overwriting the domain when an administrator logs in via localhost or internal IP.

<div class="system-param-card" style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; background-color: #f8fafc; margin: 16px 0;">
    <div class="param-header" style="font-weight: 700; color: #0f766e; font-size: 15px; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">
        ⚙️ System Configuration: Base URL &amp; Domain Freeze
    </div>
    <div class="param-row" style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px dashed #e2e8f0;">
        <div class="param-label" style="font-size: 13px; color: #334155; font-weight: 600;">Primary HTTPS Webhook Origin</div>
        <div class="param-key" style="margin-right: 12px;"><code style="background-color: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px;">web.base.url</code></div>
        <div class="param-value"><code style="background-color: #f1f5f9; color: #0f172a; padding: 2px 8px; border-radius: 4px; font-weight: 600;">https://odoo.yourcompany.com</code></div>
    </div>
    <div class="param-row" style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0;">
        <div class="param-label" style="font-size: 13px; color: #334155; font-weight: 600;">Freeze Automatic Overwrites</div>
        <div class="param-key" style="margin-right: 12px;"><code style="background-color: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px;">web.base.url.freeze</code></div>
        <div class="param-value"><code style="background-color: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 4px; font-weight: 700;">True</code></div>
    </div>
</div>

| System Parameter Key | Recommended Value | Purpose & Operational Impact |
| :--- | :--- | :--- |
| `web.base.url` | `https://odoo.yourcompany.com` | Primary public URL used to compute endpoint listeners (`/connector/in/<token>`). |
| `web.base.url.freeze` | `True` | Disables automatic domain overwrites when admins connect via localhost/internal IP. |

### 2.3 Multi-Company Topology

The connector architecture provides complete multi-company isolation:
- **Framework Presets (`connector.framework`):** Can be defined globally (`company_id` empty) or assigned to a specific company.
- **Inbound Endpoints (`connector.inbound.endpoint`):** Possess a mandatory `company_id` field (defaults to current active company). Incoming requests are evaluated within the security scope of the assigned company.
- **Inbox Messages (`connector.inbound.message`):** Inherit `company_id` from their parent endpoint.
- **Outbound Endpoints & Configs:** Partitioned by company to maintain distinct API keys and external ERP connections per legal entity.

### 2.4 User Access Rights & Security Role Matrix

`dn_connector_base` defines a strict three-tier role-based access control (RBAC) hierarchy defined in `security/security_groups.xml`:

| Security Group | XML Identifier | Intended Users | Permissions & Restrictions |
| :--- | :--- | :--- | :--- |
| **Connector User** | `dn_connector_base.group_connector_user` | Operations staff, support desk, functional managers | **Read-only access** to Framework Presets, Endpoints, and Inbox Messages. Can trigger manual retries via the "Process Now" button. **Strictly denied** access to sensitive cryptographic secrets, tokens, and Python handler code. |
| **Connector Developer** | `dn_connector_base.group_connector_developer` | Software engineers, technical integration specialists | Inherits Connector User. **Full read/write/create/unlink** permissions. Authorized to author, edit, and test custom Python Safe Eval handler code (`code` field). |
| **Administration / Settings** | `base.group_system` | Systems administrators, DevOps leads | Inherits Connector Developer. Authorized to view and modify endpoint shared secrets (`secret` field) and configure global retention settings under `res.config.settings`. |

---

## 3. Step-by-Step Configuration Guide

Follow these numbered steps to configure third-party webhook integrations from inception to production verification.

![Configuration Roadmap](/dn_connector_base/static/description/configuration_roadmap.svg)

*Figure 3.1: 4-Step Inbound Gateway Implementation Roadmap — From preset selection and listener provisioning to external platform webhook creation and live verification.*

---

### Step 1: Navigating to Connector -> Configuration -> Framework Presets

Framework Presets standardize authentication protocols, cryptographic algorithms, and header definitions for external platforms.

**UI Navigation:**
Open Odoo App Switcher -> Click **Connector** -> Under the **Configuration** menu, click **Framework Presets**.

#### 1. Built-in Framework Presets Reference
Out of the box, `dn_connector_base` installs 4 enterprise presets via `data/connector_framework_presets.xml`:

| Framework Name | Code Identifier | Auth Mode | Algorithm | Encoding | Auth Header | Prefix / Template | Default Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **🛍️ Shopify** | `shopify` | `hmac` | `SHA-256` | `base64` | `X-Shopify-Hmac-Sha256` | *(None)* | `deferred` |
| **🐙 GitHub** | `github` | `hmac` | `SHA-256` | `hex` | `X-Hub-Signature-256` | `sha256=` | `deferred` |
| **💳 Stripe** | `stripe` | `hmac` | `SHA-256` | `hex` | `Stripe-Signature` | `t={timestamp},v1={signature}` | `deferred` |
| **⚡ Generic Webhook** | `generic` | `none` | *(None)* | *(None)* | *(None)* | *(None)* | `deferred` |
| **🔑 Generic Bearer** | `generic_bearer` | `static_token`| *(None)* | *(None)* | `Authorization` | `Bearer <token>` | `deferred` |
| **🛡️ Custom HMAC** | `custom_hmac` | `hmac` | `SHA-256` | `hex` | `X-Signature` | *(Custom)* | `deferred` |

#### 2. Creating a Custom Framework Preset
When integrating systems not covered by built-in presets (e.g., custom microservices, WooCommerce, internal ESBs), administrators can create custom presets:

1. Click **New** in the Framework Presets list view.
2. In the **General Details** section:
   - **Name:** Enter a descriptive title (e.g., `Generic Bearer Token` or `Custom HMAC Gateway`).
   - **Code:** Enter a unique alphanumeric slug (e.g., `generic_bearer` or `custom_hmac`).
   - **Default Execution Mode:** Select `Deferred (Asynchronous Inbox)` for high-volume pipelines, or `Immediate (Synchronous)` if callers require immediate business responses.
3. In the **Authentication** tab:
   - **Auth Type:**
     - `No Authentication (`none`)`: Public webhook without signature checking.
     - `Static Token / Bearer (`static_token`)`: Verifies static secret against request header (supports `Bearer <token>` syntax).
     - `HTTP Basic Auth (`basic`)`: Validates Base64 encoded username/password credentials.
     - `HMAC Cryptographic Signature (`hmac`)`: Cryptographic hash verification of the raw request body.
   - **Auth Header:** Specify the HTTP request header holding the credentials (e.g., `Authorization`, `X-Signature`, or `X-API-Key`).
4. In the **HMAC Configuration** section (applicable if Auth Type is `hmac`):
   - **HMAC Algorithm:** Select `HMAC-SHA256`, `HMAC-SHA1`, or `HMAC-SHA512`.
   - **HMAC Encoding:** Choose `Hexadecimal (Lowercase)` (standard across GitHub, Stripe) or `Base64 Encoded` (standard across Shopify).
   - **HMAC Prefix:** Optional string prepended to the digest (e.g., `sha256=`). The gateway strips this prefix automatically prior to constant-time evaluation.
   - **Signature Template:** For compound headers such as Stripe, specify `t={timestamp},v1={signature}`.
5. In the **Event Routing** tab:
   - **Event Type Header:** Request header containing the event topic (e.g., `X-Event-Name`, `X-Shopify-Topic`).
   - **Event Type JSON Path:** If the event name is embedded in the JSON payload, enter the dot-notated key path (e.g., `event.type` or `action`).
   - **Idempotency Header:** Header providing a unique message ID (e.g., `X-Request-Id`, `X-Shopify-Webhook-Id`).
   - **Idempotency JSON Path:** Payload path providing unique message ID (e.g., `id` or `transaction.id`).
6. Click **Save**.

---

### Step 2: Creating and Provisioning an Inbound Endpoint

An Inbound Endpoint represents the physical network listener that accepts inbound HTTP calls for a specific integration.

**UI Navigation:**
Open Odoo App Switcher -> Click **Connector** -> Under **Inbound Gateway**, click **Endpoints** -> Click **New**.

![Endpoint Lifecycle & Configuration Flow](/dn_connector_base/static/description/endpoint_lifecycle.svg)

*Figure 3.2: Inbound Endpoint Form Structure & Parameter Routing Flow — Inspecting state transitions, routing tokens, IP whitelist filtering, circuit-breaker backpressure, and pluggable handler options.*

#### Detailed Field Configuration Reference

#### 1. Gateway Routing Section
- **Name:** Descriptive identifier (e.g., `Shopify Order Fulfillment Inbound`).
- **Framework Preset:** Select the framework configured in Step 1.
- **Token:** Automatically populated with a secure UUIDv4 string. Can be regenerated manually if a secret URL is compromised.
- **Endpoint URL:** Computed automatically as `[web.base.url]/connector/in/[token]`. Includes a **Copy to Clipboard** icon for fast extraction.
- **Allowed Methods:** Select `POST Only` (recommended for standard webhooks), `POST & PUT`, or `All (GET, POST, PUT, PATCH)`. Non-matching HTTP methods return HTTP 405 (`Method Not Allowed`).
- **State:**
  - `Draft`: Returns HTTP 404 (`Endpoint not found`). Use during initial creation.
  - `Active`: Actively processes incoming HTTP traffic.
  - `Paused`: Returns HTTP 503 (`Service Unavailable`). Use during ERP maintenance windows or migrations. External webhook callers will pause or queue deliveries.

#### 2. Security & Network Section
- **Auth Override:** Set to `Inherit Framework Auth` to respect framework defaults. To customize authentication specifically for this endpoint, select `Public / None`, `Static Token`, or `HMAC Signature`.
- **Secret:** Enter the cryptographic secret key or static Bearer token shared with the external service.
  > [!NOTE]
  > This field is protected by Odoo security groups and is only visible to users belonging to the `Administration / Settings` (`base.group_system`) group.
- **IP Allowlist:** Restrict network access by entering trusted IP addresses or CIDR subnets (separated by commas or newlines).
  - *Example single IPs:* `54.240.196.1, 54.240.196.2`
  - *Example CIDR subnet:* `192.168.1.0/24, 10.0.0.0/8`
  - *Behavior:* If populated, requests originating from non-whitelisted IPs are rejected immediately with HTTP 403 (`Forbidden`).
- **Max Backlog (Circuit Breaker):** Configurable integer (default `10000`). If the count of pending messages in the inbox (`queued` + `processing`) reaches this limit, the gateway triggers backpressure, immediately rejecting new requests with HTTP 429 (`Too Many Requests`) and transmitting a `Retry-After: 30` header. This prevents database resource exhaustion during large cron processing backlogs.

#### 3. Handler Configuration Tab
- **Handler Type:** Determines how payload data is handled upon ingestion:
  - `Store Only (Inbox Archive)`: Persists payload, headers, and metadata in the inbox. Performs no ORM processing. Useful for audit logging and data capture.
  - `Raw Model (Auto Schema x_*)`: Automatically instantiates staging records in a target model (specified in `target_model_id`), storing payload in `x_payload` and external ID in `x_external_id`.
  - `Server Action (ir.actions.server)`: Invokes an Odoo automated Server Action with active context variables (`active_id`, `active_model`, `payload`, `headers`).
  - `Python Safe Eval Code`: Sandboxed Python script executed inside a secured environment. Full access to `payload`, `headers`, `message`, `env`, `datetime`, `json`, `re`, `math`, and dynamic imports (`_dynamic_import`).
  - `Connector Pack Handler`: Delegates message processing to registered downstream connector packs (e.g., Vietnam Address Connector `vn_address_v1`).
- **Execution Mode:**
  - `Deferred (Async Inbox)` *(Recommended)*: Writes payload to `connector.inbound.message` in `queued` state and immediately returns HTTP 202 (`Accepted`). Background cron workers execute the business transformation asynchronously.
  - `Immediate (Sync)`: Executes the handler synchronously within the HTTP request thread. Returns HTTP 200 containing handler results upon completion.
- **Response Mode:**
  - `Fast Acknowledgment JSON (`ack`)`: Returns standard gateway JSON status: `{"status": "queued", "uuid": "<uuid>"}`.
  - `Handler Result (`handler_result`)`: Applicable when execution mode is `immediate`. Returns the exact JSON dictionary output assigned to `result` by the Python handler.
- **Sequential Ordering (`ordering_key`):**
  - `Parallel Processing (`none`)`: Cron workers claim and process messages concurrently.
  - `Sequential by Entity ID (`entity_id`)`: Extracts entity ID using `ordering_json_path` (default `id`). If an earlier message for the same entity ID is pending (`queued`, `processing`, or `failed`), newer messages are held back, guaranteeing chronological order (e.g., Customer Create processed before Customer Update).
  - `Sequential by Event Type (`event_type`)`: Guarantees chronological execution per event topic.

---

### Step 3: Configuring Webhooks on External Platforms

#### Scenario A: Shopify Admin Webhook Integration

1. Log in to your **Shopify Store Admin** (`https://admin.shopify.com/store/<your-store>`).
2. Navigate to **Settings** (gear icon bottom left) -> **Notifications**.
3. Scroll to the bottom section titled **Webhooks** and click **Create webhook**.
4. Configure the webhook parameters:
   - **Event:** Select the trigger event (e.g., `Order creation`, `Order update`, or `Customer creation`).
   - **Format:** Select `JSON`.
   - **URL:** Paste the computed **Endpoint URL** from your Odoo Inbound Endpoint form (e.g., `https://odoo.yourcompany.com/connector/in/9f8a3c21-4b72-4d1e-8e9a-653c071d1822`).
   - **Webhook API version:** Select the latest stable version (e.g., `2025-01`).
5. Click **Save**.
6. **Copy Secret Key:** Scroll to the bottom of the Webhooks table in Shopify to the notice: *"All your webhooks will be signed with a secret: `<secret_key>`"*. Copy this string.
7. Return to Odoo -> Open your Shopify Inbound Endpoint form -> Paste the copied key into the **Secret** field -> Click **Save**.

<div style="border-left: 4px solid #0f766e; background-color: #f0fdfa; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
    <strong style="color: #0f766e;">🛍️ Shopify Cryptographic Webhook Specification</strong><br/>
    • <strong>Header:</strong> <code>X-Shopify-Hmac-Sha256</code><br/>
    • <strong>Algorithm:</strong> <code>HMAC-SHA256</code> | <strong>Encoding:</strong> <code>Base64</code><br/>
    • <strong>Framework Preset:</strong> <code>preset_framework_shopify</code> (Code: <code>shopify</code>)
</div>

---

#### Scenario B: GitHub Repository Webhooks

1. Open your repository on GitHub (`https://github.com/<org>/<repo>`).
2. Click **Settings** (top navigation bar) -> In the left sidebar, click **Webhooks** -> Click **Add webhook**.
3. Configure the webhook parameters:
   - **Payload URL:** Paste your Odoo Endpoint URL (`https://odoo.yourcompany.com/connector/in/<token>`).
   - **Content type:** Select `application/json`.
   - **Secret:** Enter a strong random secret phrase (e.g., `gh_sec_99a8b7c6d5e4f3a2b1`).
   - **SSL verification:** Ensure *Enable SSL verification* is selected.
   - **Which events would you like to trigger this webhook?:** Select *Just the push event* or *Let me select individual events* (e.g., `Issues`, `Pull requests`, `Releases`).
4. Click **Add webhook**.
5. Return to Odoo -> Open your GitHub Inbound Endpoint form -> Paste the exact secret phrase into the **Secret** field -> Click **Save**.

<div style="border-left: 4px solid #0284c7; background-color: #f0f9ff; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
    <strong style="color: #0284c7;">🐙 GitHub Cryptographic Webhook Specification</strong><br/>
    • <strong>Header:</strong> <code>X-Hub-Signature-256</code><br/>
    • <strong>Algorithm:</strong> <code>HMAC-SHA256</code> | <strong>Encoding:</strong> <code>Hexadecimal (Lowercase)</code><br/>
    • <strong>Prefix:</strong> <code>sha256=</code> (Stripped automatically by Odoo gateway)<br/>
    • <strong>Framework Preset:</strong> <code>preset_framework_github</code> (Code: <code>github</code>)
</div>

---

#### Scenario C: Stripe Dashboard Webhook Integration

1. Log in to the **Stripe Dashboard** (`https://dashboard.stripe.com/`).
2. Navigate to **Developers** -> **Webhooks**.
3. Click **Add destination** (or **Add endpoint**).
4. Configure the webhook destination:
   - **Endpoint URL:** Paste your Odoo Endpoint URL (`https://odoo.yourcompany.com/connector/in/<token>`).
   - **Description:** Enter `Odoo 19 Production Inbound Listener`.
   - **Select events to listen to:** Select events (e.g., `payment_intent.succeeded`, `checkout.session.completed`, `customer.subscription.updated`).
5. Click **Add endpoint**.
6. **Reveal Signing Secret:** In the newly created endpoint screen, locate the section **Signing secret**. Click **Reveal** to view the key starting with `whsec_...` (e.g., `whsec_a1b2c3d4e5...`).
7. Return to Odoo -> Open your Stripe Inbound Endpoint form -> Paste the `whsec_...` key into the **Secret** field -> Click **Save**.

<div style="border-left: 4px solid #7c3aed; background-color: #faf5ff; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
    <strong style="color: #7c3aed;">💳 Stripe Timestamped Cryptographic Webhook Specification</strong><br/>
    • <strong>Header:</strong> <code>Stripe-Signature</code><br/>
    • <strong>Signature Template:</strong> <code>t={timestamp},v1={signature}</code><br/>
    • <strong>Signed String:</strong> <code>{timestamp}.{raw_body}</code><br/>
    • <strong>Algorithm:</strong> <code>HMAC-SHA256</code> | <strong>Encoding:</strong> <code>Hexadecimal (Lowercase)</code><br/>
    • <strong>Framework Preset:</strong> <code>preset_framework_stripe</code> (Code: <code>stripe</code>)
</div>

---

#### Scenario D: Generic REST Client / Microservice (cURL Verification)

For custom systems utilizing Bearer tokens or HMAC signatures, verify network connectivity and authentication using `curl`.

##### Example 1: Testing Static Bearer Token Authentication
```bash
curl -X POST "https://odoo.yourcompany.com/connector/in/your-endpoint-token" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer my-secret-bearer-token-12345" \
     -H "X-Idempotency-Key: test-req-001" \
     -d '{"event": "inventory_sync", "sku": "WIDGET-01", "quantity": 150}'
```
**Expected Response (HTTP 202 Accepted):**
```json
{
  "status": "queued",
  "uuid": "4c98a21e-128b-4bfe-9852-6a5cf2bda621"
}
```

##### Example 2: Testing HMAC-SHA256 Hex Signature
```bash
# 1. Payload and Secret
PAYLOAD='{"event":"order_created","id":98765,"amount":299.95}'
SECRET="my_hmac_secret_key"

# 2. Compute HMAC-SHA256 Hex Digest
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

# 3. Transmit HTTP Request
curl -X POST "https://odoo.yourcompany.com/connector/in/your-endpoint-token" \
     -H "Content-Type: application/json" \
     -H "X-Signature: $SIGNATURE" \
     -H "X-Idempotency-Key: req-order-98765" \
     -d "$PAYLOAD"
```

---

## 4. Operations, Queue Management & Troubleshooting

### 4.1 Inbound Message Lifecycle & State Machine

Incoming events are tracked in the transactional inbox table `connector.inbound.message`. The state machine governs the lifecycle of each payload:

```mermaid
stateDiagram-v2
    [*] --> received: Fast Receiver Ingests HTTP Call
    received --> queued: Async Execution Mode (Default)
    received --> processing: Sync Execution Mode (Immediate)
    queued --> processing: Cron Claims via FOR UPDATE SKIP LOCKED
    processing --> done: Handler Finishes (HTTP 200 Recorded)
    processing --> failed: Exception Raised & attempts < max_attempts
    failed --> processing: next_retry_at Timer Expires
    processing --> dead: Exception Raised & attempts >= max_attempts (DLQ)
    received --> skipped: Duplicate Idempotency Key Detected
    queued --> skipped: Duplicate Key in Concurrency Collision
```

#### Message States Defined

| State | Badge Color | Meaning & Operational Implication |
| :--- | :--- | :--- |
| `received` | Info (Blue) | Transient initial state during controller ingestion. |
| `queued` | Info (Blue) | Message persisted in inbox; awaiting claim by background batch processor. |
| `processing` | Warning (Yellow)| Worker thread has locked the row and is executing the configured handler. |
| `done` | Success (Green) | Processing succeeded. Duration and response output are recorded. |
| `failed` | Warning (Yellow)| Processing failed with an exception. Awaiting automatic retry backoff. |
| `dead` | Danger (Red) | Max retry attempts exhausted. Message quarantined in Dead Letter Queue. |
| `skipped` | Muted (Grey) | Idempotent duplicate detected. No processing required. |

---

### 4.2 Monitoring the Transactional Inbox

**UI Navigation:**
Open Odoo App Switcher -> Click **Connector** -> Under **Inbound Gateway**, click **Inbox Messages**.

The list view displays real-time ingestion status with the following columns:
- **Received At:** Timestamp down to the millisecond.
- **UUID:** Globally unique tracking identifier.
- **Endpoint:** Target listener that accepted the message.
- **Event Type:** Extracted event topic (e.g., `orders/create`, `push`).
- **Idempotency Key:** Deduplication identifier.
- **Attempts:** Number of execution attempts executed so far.
- **Duration (ms):** Total execution runtime in milliseconds.
- **State:** Color-coded status badge (`queued`, `processing`, `done`, `dead`, `failed`).

#### Detailed Message Form View Tabs
Clicking any message reveals diagnostic details:
1. **Payload Tab:** Formatted JSON data sent by the external system.
2. **Headers Tab:** Key-value map of all incoming HTTP headers (including forwarding headers and signatures).
3. **Raw Body Tab:** Exact raw byte representation of the payload as received over the wire.
4. **Response Tab:** JSON response returned by the handler upon completion.
5. **Diagnostic Traceback Tab:** Visible if errors occurred. Contains the exact Python exception type (`error_type`) and full stack traceback (`error_details`).

---

### 4.3 Concurrency Engine: High-Worker Execution via `SKIP LOCKED`

The inbound queue processor cron job (`ir_cron_inbound_process`, titled *"Connector Inbound: Batch Processor"*) executes every 1 minute.

#### Ground-Truth Concurrency Query
Under the hood, `_cron_process()` executes the following SQL query wrapped in `odoo.tools.SQL`:

```sql
SELECT id FROM connector_inbound_message
WHERE state IN ('queued', 'failed')
  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
ORDER BY priority DESC, received_at ASC, id ASC
LIMIT <batch_size>
FOR UPDATE SKIP LOCKED;
```

#### Why `FOR UPDATE SKIP LOCKED` Matters for DevOps
In multi-worker Odoo deployments (e.g., `workers = 8` or Kubernetes pods running multiple instances):
- **Zero Lock Contention:** When Worker A claims a batch of 100 messages, it locks those specific rows. When Worker B runs simultaneously, `SKIP LOCKED` instructs PostgreSQL to bypass locked rows and immediately lock the *next* batch of 100 messages.
- **No Worker Starvation:** Multiple cron workers process the queue in parallel without deadlocks, serialization anomalies, or thread blocking.
- **Strict Priority Sorting:** Messages marked with `Urgent (3)` or `High (2)` priority are claimed before `Normal (1)` or `Low (0)`.

---

### 4.4 Dead Letter Queue (DLQ) & Operator Recovery Protocol

When an incoming payload contains malformed data or triggers an unhandled business error, the gateway quarantines the message rather than dropping it.

#### 1. Exponential Backoff with Randomized Jitter
If an error occurs and `attempts < max_attempts` (default 5):
1. The message state changes to `failed`.
2. The system computes a retry delay:
   $$\text{Delay} = \min(3600, 10 \times 2^{\text{attempts}}) + \text{Random Jitter}$$
3. A timestamp is written to `next_retry_at`. The cron will ignore this message until the timer expires.
4. If attempts reach `max_attempts` (5), state transitions to `dead` (quarantined).

#### 2. Operator Recovery Workflow
When a message enters the Dead Letter Queue:
1. Navigate to **Connector -> Inbound Gateway -> Dead Letter Queue**.
2. Open the affected message record.
3. Review the **Diagnostic Traceback** tab:
   - *Example: `KeyError: 'billing_address'` indicates missing payload fields.*
   - *Example: `UserError: Product [SKU-99] not found` indicates master data missing in Odoo.*
4. **Resolve the Root Cause:**
   - If master data is missing (e.g., product, partner, tax), configure the required record in Odoo.
   - If payload data is malformed, click into the **Payload** JSON field and edit the parameters directly.
5. **Re-Execute the Message:** Click the **Process Now** button in the form view header.
   - The message resets to `processing` and immediately executes the configured handler.
   - If successful, the state transitions to `done`, recording duration and response output.
   - If execution fails again, the updated error traceback is recorded.

---

### 4.5 Sequential FIFO Entity Ordering (`ordering_key`)

In event-driven architectures, race conditions can cause data corruption if events arrive or execute out of order (e.g., an `order.cancelled` webhook processed before `order.created`).

`dn_connector_base` resolves this via the `ordering_key` setting on the endpoint:
1. **Configuration:** On the Inbound Endpoint form, set **Ordering Key** to `Sequential by Entity ID` and specify **Ordering JSON Path** as `id` (or `order_number`).
2. **Execution Guard:** During batch processing, the processor invokes `_is_blocked_by_ordering()`:
   ```python
   earlier_count = self.search_count([
       ("endpoint_id", "=", self.endpoint_id.id),
       ("ordering_key", "=", self.ordering_key),
       ("id", "<", self.id),
       ("state", "in", ["queued", "processing", "failed"]),
   ])
   ```
3. **Sequential Guarantee:** If an earlier message for entity `ORDER-1001` is currently in `queued`, `processing`, or `failed` state, subsequent messages for `ORDER-1001` are skipped until the prior message reaches `done` (or is manually resolved). Other orders (`ORDER-1002`) continue processing in parallel.

---

## 5. System Settings, Retention & Maintenance

System-wide operational parameters are centralized under Odoo Settings.

**UI Navigation:**
Open Odoo App Switcher -> Click **Connector** -> Under **Configuration**, click **Settings** (or open **General Settings** -> scroll to **Connector**).

![Retention & Dead Letter Queue Maintenance Flow](/dn_connector_base/static/description/retention_maintenance_flow.svg)

*Figure 5.1: Retention Engine & Dead Letter Queue Architecture — Automated daily purging, exponential retry calculation with jitter, and operator DLQ recovery.*

<div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; background-color: #ffffff; margin: 16px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <div style="font-weight: 700; color: #1e293b; font-size: 15px; margin-bottom: 12px; border-bottom: 2px solid #0f766e; padding-bottom: 6px;">
        ⚙️ Connector Inbound Gateway Configuration Panel (<code>res.config.settings</code>)
    </div>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px; font-weight: 600; color: #334155;">Message Retention (Done)</td>
            <td style="padding: 10px; color: #64748b;">Days to retain successfully processed messages before purge.</td>
            <td style="padding: 10px; text-align: right;"><code style="background-color: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-weight: 700; color: #0f766e;">30 Days</code></td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px; font-weight: 600; color: #334155;">Dead Letter Retention</td>
            <td style="padding: 10px; color: #64748b;">Days to retain dead letters for debugging before purge.</td>
            <td style="padding: 10px; text-align: right;"><code style="background-color: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-weight: 700; color: #e11d48;">90 Days</code></td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px; font-weight: 600; color: #334155;">Batch Processing Size</td>
            <td style="padding: 10px; color: #64748b;">Number of messages claimed per batch by processor cron.</td>
            <td style="padding: 10px; text-align: right;"><code style="background-color: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-weight: 700; color: #0284c7;">100 Messages</code></td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px; font-weight: 600; color: #334155;">Message Lock Timeout</td>
            <td style="padding: 10px; color: #64748b;">Timeout threshold in seconds for worker lock contention.</td>
            <td style="padding: 10px; text-align: right;"><code style="background-color: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-weight: 700; color: #7c3aed;">60 Seconds</code></td>
        </tr>
    </table>
</div>

### 5.1 System Parameters & Defaults Reference

| Setting UI Name | Technical Config Parameter | Default | Operational Impact & Recommendations |
| :--- | :--- | :--- | :--- |
| **Message Retention (Done)** | `dn_connector_base.retention_days_done` | `30` | Number of days successfully executed (`done`) messages are kept for audit before deletion. High-volume systems (>50k msgs/day) should reduce this to `7` or `14` to keep table size lean. |
| **Dead Letter Retention** | `dn_connector_base.retention_days_dead` | `90` | Number of days quarantined (`dead`) poison pills are retained. Provides operational buffer for developers to patch bugs and replay historical payloads. |
| **Batch Processing Size** | `dn_connector_base.default_batch_size` | `100` | Messages claimed per cron execution. Increase to `250` or `500` if queue growth outpaces processing velocity. |
| **Message Lock Timeout** | `dn_connector_base.lock_timeout` | `60` | Operational timeout threshold for row lock contention in multi-worker environments. |

### 5.2 Scheduled Cron Jobs Reference

Verify and manage background jobs under **Settings -> Technical -> Automation -> Scheduled Actions**:

| Cron Job Name | Technical Identifier | Execution Interval | Model & Method |
| :--- | :--- | :--- | :--- |
| **Connector Inbound: Batch Processor** | `ir_cron_inbound_process` | Every 1 minute | `connector.inbound.message._cron_process()` |
| **Connector Inbound: Retention Purge** | `ir_cron_inbound_retention`| Every 1 day | `connector.inbound.message._cron_cleanup_retention()` |
| **Connector: Outbound Scheduled Sync**| `ir_cron_connector_sync` | Every 1 hour | `connector.outbound.endpoint._cron_sync_all_endpoints()` |

> [!TIP]
> The Retention Purge cron executes database deletions in chunks of 5,000 records (`search(..., limit=5000).unlink()`). This prevents table locking on high-volume production PostgreSQL databases.

---

## 6. Production Hardening & Infrastructure Deployment

Deploying webhooks in mission-critical enterprise environments requires proper proxy termination, rate limiting, and database routing.

### 6.1 Nginx Reverse Proxy Production Configuration

Place the following configuration block inside your Nginx server configuration (`/etc/nginx/sites-available/odoo.conf`):

```nginx
# Define rate limiting zone for inbound webhooks (10MB memory, 100 requests/sec limit)
limit_req_zone $binary_remote_addr zone=odoo_webhook_limit:10m rate=100r/s;

upstream odoo_backend {
    server 127.0.0.1:8019;
    keepalive 32;
}

upstream odoo_chat {
    server 127.0.0.1:8072;
}

server {
    listen 443 ssl http2;
    server_name odoo.yourcompany.com;

    # SSL/TLS Hardening
    ssl_certificate /etc/letsencrypt/live/odoo.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/odoo.yourcompany.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Maximum payload size (matches Odoo connector limit + headers)
    client_max_body_size 15M;

    # Security Headers
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Frame-Options SAMEORIGIN;

    # =========================================================================
    # DEDICATED INBOUND GATEWAY WEBHOOK ROUTE
    # =========================================================================
    location ~* ^/connector/in/ {
        # Apply rate limiting: allow bursts up to 50 requests without artificial delay
        limit_req zone=odoo_webhook_limit burst=50 nodelay;

        # Forward real client IP addresses for IP Allowlist verification
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $http_host;

        # In multi-tenant environments, pin database explicitly to bypass selector
        # proxy_set_header X-Odoo-dbfilter ^odoo19$;

        proxy_redirect off;
        proxy_buffering off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;

        proxy_pass http://odoo_backend;
    }

    # Standard Odoo Web Interface & API Routes
    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_pass http://odoo_backend;
    }

    # Longpolling / Websocket Route
    location /websocket {
        proxy_pass http://odoo_chat;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.2 Multi-Database Environments & `dbfilter` Routing

In Odoo instances hosting multiple databases, public routes like `/connector/in/<token>` cannot display the database selection screen (`/web/database/selector`) without causing external webhooks to fail with HTTP 303 or HTTP 500.

#### Resolution Strategies:
1. **Subdomain-Based Routing:** Configure `dbfilter = ^%d$` in `/opt/odoo19.conf` so each database matches its hostname (e.g., `prod.yourcompany.com` routes to database `prod`).
2. **Exact Database Pinning via Nginx:** If using a shared hostname, inject the database name header directly in Nginx for the webhook path:
   ```nginx
   location ~* ^/connector/in/ {
       proxy_set_header X-Odoo-dbfilter ^odoo19$;
       proxy_pass http://odoo_backend;
   }
   ```
3. **Dedicated Configuration File:** In single-database production environments, pin the database name explicitly in `/opt/odoo19.conf`:
   ```ini
   [options]
   db_name = odoo19
   list_db = False
   ```

### 6.3 Security Hardening & Secret Rotation Protocol

1. **Credential Rotation:** If an endpoint URL or shared secret is compromised:
   - Open the Inbound Endpoint form.
   - Click the **Token** field and generate a new UUIDv4 string.
   - Update the **Secret** field with a new cryptographic key.
   - Update the webhook destination URL and secret on the third-party platform (Shopify, GitHub, Stripe).
2. **Access Revocation:** Use the **State** toggle to switch the endpoint to `Paused` immediately during security incidents or external denial-of-service events.
3. **Database Backup Isolation:** Staged payload data in `connector.inbound.message` contains sensitive customer and transactional payloads. Ensure that off-site PostgreSQL backup archives are encrypted at rest using AES-256.

---

## 7. Administrator FAQ & Operational Troubleshooting

### Q1: The external platform reports HTTP 404 when sending webhooks.
- **Cause 1:** The endpoint state in Odoo is set to `Draft`. Change state to `Active`.
- **Cause 2:** The token in the URL does not match the token on the endpoint record.
- **Cause 3:** Multi-database routing issue where Odoo redirects to `/web/database/selector`. Verify `dbfilter` or `db_name` in `/opt/odoo19.conf`.

### Q2: The external platform reports HTTP 401 Unauthorized.
- **HMAC Signatures:** Verify that the secret key configured on the Odoo endpoint exactly matches the signing secret on the external platform. Ensure there are no accidental leading/trailing spaces.
- **Prefix Errors:** For GitHub, verify that `hmac_prefix` is set to `sha256=`.
- **Encoding Errors:** For Shopify, verify that `hmac_encoding` is set to `base64`. For GitHub and Stripe, verify it is set to `hex`.
- **Timestamp Desync:** For Stripe, verify that system clock NTP synchronization is active on the Odoo Linux host (`chrony` or `systemd-timesyncd`).

### Q3: The external platform reports HTTP 403 Forbidden.
- The sender IP address is not included in the endpoint's `ip_allowlist`.
- Check if your reverse proxy is properly setting `X-Forwarded-For`. If Nginx forwards `127.0.0.1` as the client IP, add `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` to your Nginx configuration.

### Q4: The external platform reports HTTP 429 Too Many Requests.
- The backlog circuit breaker has engaged because `queued` + `processing` messages reached `max_backlog` (default 10,000).
- Check if the batch processor cron (`ir_cron_inbound_process`) is active and running.
- Increase the worker batch size under **Connector -> Configuration -> Settings** to process backlog faster.

### Q5: Messages remain in `queued` state and are never processed.
- Verify that the scheduled action *"Connector Inbound: Batch Processor"* (`ir_cron_inbound_process`) is enabled (`active=True`).
- Verify that Odoo is running with cron threads enabled (`max_cron_threads >= 1` in `/opt/odoo19.conf`).
- Inspect Odoo server logs for any unhandled exceptions during cron bootstrap.

---

*End of Administrator & Operator Setup Guide.*
