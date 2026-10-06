# VNPay Payment Integration for Odoo 19
## Module: `dn_payment_vnpay` + Enhancements to `dn_payment_connector_base`

> Implementation Plan v2 — Generated 2026-10-02

---

## 1. Executive Summary

This document defines the architecture and implementation plan for integrating VNPay payment gateway
into Odoo 19, built on top of the `dn_payment_connector_base` framework (renamed from `payment_connector_base`).

### Design Philosophy

> **`dn_payment_connector_base` is the SINGLE framework that contains ALL generic methods.**
> **`dn_payment_vnpay` depends on it and provides ONLY data (XML records) + minimal VNPay-specific overrides.**
> **All new methods added to `dn_payment_connector_base` must remain generic and reusable by future providers (MoMo, ZaloPay, GHN, etc.).**

### What "generic" means in practice

Every method added to `dn_payment_connector_base` must:
- Accept provider-agnostic parameters (no `vnpay_*` hardcoded names)
- Be configurable through `connector.setting`, `connector.mapping`, or `connector.hash.method` records
- Work for any provider that follows the same pattern (sorted-params hash, pipe-separated hash, redirect URL, JSON API call, webhook callback)

---

## 2. VNPay API Analysis

### 2.1 API Capabilities

| Feature | VNPay Command | HTTP Method | Endpoint |
|---------|--------------|-------------|----------|
| **Payment URL** | `pay` | GET (redirect) | `paymentv2/vpcpay.html` |
| **IPN Callback** | — | GET (webhook) | Merchant IPN URL |
| **Return URL** | — | GET (redirect back) | Merchant Return URL |
| **Query Transaction** | `querydr` | POST (JSON) | `merchant_webapi/api/transaction` |
| **Refund** | `refund` | POST (JSON) | `merchant_webapi/api/transaction` |
| **Installment** | `pay` + extra params | GET (redirect) | `paymentv2/vpcpay.html` |
| **Token Payment** | `pay_and_create` / `token_pay` | POST (JSON) | Token endpoint |
| **Bank List** | — | POST | `qrpayauth/api/merchant/get_bank_list` |

### 2.2 Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `vnp_TmnCode` | Merchant terminal code (8 chars) | `2QXUI4B4` |
| `vnp_HashSecret` | Secret key for HMAC-SHA512 | (secret key) |
| `vnp_Version` | API version | `2.1.0` |

### 2.3 Hash Algorithms

**Payment URL hash (sorted query-string):**
```
1. Collect all vnp_* params (exclude vnp_SecureHash, vnp_SecureHashType)
2. Sort alphabetically by key
3. URL-encode both keys and values
4. Join: urlencode(key1)=urlencode(value1)&urlencode(key2)=urlencode(value2)&...
5. HMAC-SHA512(secret, queryString) → lowercase hex
```

**QueryDR/Refund hash (pipe-separated):**
```
data = field1|field2|field3|...|fieldN
HMAC-SHA512(secret, data) → lowercase hex
```

### 2.4 Response Codes

| Code | Meaning |
|------|---------|
| `00` | Success |
| `07` | Deducted but suspected fraud |
| `09` | Card not registered for InternetBanking |
| `10` | Incorrect auth > 3 times |
| `11` | Payment timeout |
| `12` | Card/Account locked |
| `13` | Wrong OTP |
| `24` | Customer cancelled |
| `51` | Insufficient balance |
| `65` | Over daily limit |
| `75` | Bank under maintenance |
| `79` | Wrong password too many times |
| `97` | Invalid checksum |
| `99` | Other error |

---

## 3. Current State of `payment_connector_base`

### 3.1 Models (All Implemented ✅)

| Model | Status | Notes |
|-------|--------|-------|
| `connector.provider` | ✅ Complete | Provider, settings, environments |
| `connector.environment` | ✅ Complete | Sandbox/Production base URLs |
| `connector.setting` | ✅ Complete | Key-value with encryption |
| `connector.api` | ✅ Complete | API definitions per provider |
| `connector.endpoint` | ✅ Complete | URL, method, body type, hash method |
| `connector.mapping` | ✅ Complete | HEADER/QUERY/PAYLOAD/RESPONSE |
| `connector.mapping.line` | ✅ Complete | FIELD/SETTING/FIXED/VARIABLE/EXPRESSION sources |
| `connector.compute.pipeline` | ✅ Complete | Transform chain |
| `connector.compute.function` | ✅ Complete | 40+ builtin functions incl. `bank_amount`, `url_encode` |
| `connector.hash.method` | ✅ Complete | MD5/SHA1/SHA256/SHA512/HMAC-SHA256/HMAC-SHA512/Custom |
| `connector.auth.method` | ✅ Complete | API Key/Basic/Bearer/JWT/OAuth2/HMAC/Custom |
| `connector.execution` | ✅ Complete | Execution tracking with steps |
| `connector.execution.step` | ✅ Complete | Step tracking |
| `connector.request.log` | ✅ Complete | Request logging |
| `connector.response.log` | ✅ Complete | Response logging |
| `connector.error.log` | ✅ Complete | Error logging |
| `connector.plugin` | ✅ Complete | Custom Python class plugins |

### 3.2 Service Engines (Most Are Stubs ⚠️)

| Engine | File | Status | What's Missing |
|--------|------|--------|---------------|
| `ExecutionEngine` | `execution_engine.py` | ⚠️ Partial | Pipeline orchestration exists but engine calls are stubs |
| `LoadEngine` | `load_engine.py` | ❌ Stub | `load_source_data()` returns `{}` |
| `MappingEngine` | `mapping_engine.py` | ❌ Stub | `build_mapping()` returns `{}` |
| `ComputeEngine` | `compute_engine.py` | ❌ Stub | `execute_pipeline()` returns input |
| `AuthEngine` | `auth_engine.py` | ❌ Stub | `authenticate()` returns `{}` |
| `HashEngine` | `hash_engine.py` | ❌ Stub | `generate_hash()` returns `''` |
| `HTTPEngine` | `http_engine.py` | ❌ Stub | `send_request()` returns `{}` |
| `ResponseEngine` | `response_engine.py` | ❌ Stub | `parse_response()` returns `{}` |
| `BusinessEngine` | `business_engine.py` | ❌ Stub | `execute_actions()` returns `{}` |
| `LoggingEngine` | `logging_engine.py` | ✅ Complete | Request/response/error logging |

### 3.3 What Already Works Well

- **`connector.hash.method`** model already has full `hash()` method with HMAC-SHA512 + `build_signature_string()` for sorted key=value
- **`connector.compute.function`** already has `bank_amount` (×100), `url_encode`, `format_date`, `uuid` etc.
- **`connector.mapping.line`** already resolves FIELD/SETTING/FIXED/VARIABLE/EXPRESSION/CONTEXT sources
- **`connector.mapping`** already has `build_dict()` that iterates lines

---

## 4. Enhancements to `dn_payment_connector_base`

> [!IMPORTANT]
> Every method below is **generic** — no VNPay-specific logic. Provider-specific behavior
> is configured through `connector.setting`, `connector.mapping`, and `connector.hash.method` records.

### 4.1 `services/hash_engine.py` — Full Implementation

**Current:** Stub returning `''`

**Enhancement:** Implement using the existing `connector.hash.method` model (which already has all the logic).

```python
class HashEngine(models.AbstractModel):
    _name = 'connector.hash.engine'

    @api.model
    def generate_hash(self, context):
        """Use endpoint's hash_method_id to generate hash from context data."""
        hash_method = context.endpoint.hash_method_id
        if not hash_method:
            return ''
        secret = context.provider.get_setting('hash_secret', context.environment.id)
        data = context.get_variable('hash_data')
        return hash_method.hash(data, secret, context)

    @api.model
    def build_sorted_query_hash(self, params, secret, algorithm='hmac_sha512'):
        """
        Generic: Build hash from sorted URL-encoded query parameters.
        Pattern used by: VNPay (payment URL), and many other Asian gateways.
        
        1. Sort params alphabetically by key
        2. URL-encode keys and values
        3. Join with '&'
        4. HMAC(secret, query_string)
        """

    @api.model
    def build_pipe_separated_hash(self, fields_list, values_dict, secret, algorithm='hmac_sha512'):
        """
        Generic: Build hash from pipe-separated field concatenation.
        Pattern used by: VNPay (querydr/refund), and some banking APIs.
        
        1. Concatenate values in field order with '|'
        2. HMAC(secret, pipe_string)
        """

    @api.model
    def verify_hash(self, received_hash, params, secret, algorithm='hmac_sha512',
                    hash_style='sorted_query', exclude_keys=None, pipe_fields=None):
        """
        Generic: Verify a received hash against computed hash.
        
        Args:
            hash_style: 'sorted_query' or 'pipe_separated'
            exclude_keys: Keys to exclude from hash computation (e.g., ['vnp_SecureHash'])
            pipe_fields: Ordered list of fields for pipe-separated hash
        Returns:
            bool
        """
```

### 4.2 `services/http_engine.py` — Full Implementation

**Current:** Stub returning `{}`

**Enhancement:** Implement actual HTTP calls using Python `requests` library.

```python
class HTTPEngine(models.AbstractModel):
    _name = 'connector.http.engine'

    @api.model
    def send_request(self, context):
        """
        Send HTTP request based on endpoint configuration.
        Reads method, URL, headers, body from context.
        Supports GET, POST, PUT, PATCH, DELETE.
        Handles timeout, retry, error logging.
        
        Returns:
            {
                'success': bool,
                'status_code': int,
                'response_body': str,
                'response_headers': dict,
                'duration': float,
            }
        """

    @api.model
    def build_redirect_url(self, base_url, params, hash_key='vnp_SecureHash',
                           hash_value=None):
        """
        Generic: Build a full redirect URL with query parameters and hash.
        Pattern used by: VNPay, MoMo, ZaloPay (redirect-based payments).
        
        1. URL-encode params
        2. Append hash parameter
        3. Return full URL: base_url?param1=val1&param2=val2&hash_key=hash_value
        
        Args:
            base_url: The gateway URL
            params: dict of parameters (already sorted if needed)
            hash_key: Name of the hash parameter to append
            hash_value: The computed hash
        Returns:
            str: Full redirect URL
        """
```

### 4.3 `services/mapping_engine.py` — Full Implementation

**Current:** Stub returning `{}`

**Enhancement:** Wire up to existing `connector.mapping` and `connector.mapping.line` models.

```python
class MappingEngine(models.AbstractModel):
    _name = 'connector.mapping.engine'

    @api.model
    def build_mapping(self, context, mapping_type):
        """
        Build mapping dict from connector.mapping records for this API.
        Uses mapping.build_dict(context) which already iterates lines.
        
        Args:
            mapping_type: 'HEADER', 'QUERY', 'PATH', 'PAYLOAD', 'RESPONSE'
        Returns:
            dict
        """

    @api.model
    def build_sorted_params(self, params, exclude_keys=None):
        """
        Generic: Sort params alphabetically, URL-encode keys and values.
        Pattern used by: VNPay, MoMo, and many payment gateways.
        
        Returns:
            str: Sorted URL-encoded query string
        """

    @api.model
    def resolve_mapping_for_record(self, api_record, source_record, mapping_type, context=None):
        """
        Generic: Resolve a full mapping dict for a given source record.
        Walks mapping lines, resolves FIELD/SETTING/FIXED sources,
        runs compute pipelines, applies data type conversions.
        
        Returns:
            dict: Fully resolved parameter dict
        """
```

### 4.4 `services/load_engine.py` — Full Implementation

**Current:** Stub returning `{}`

```python
class LoadEngine(models.AbstractModel):
    _name = 'connector.load.engine'

    @api.model
    def load_source_data(self, context):
        """
        Load source record data into context variables.
        Reads the source record (context.record) and extracts
        fields referenced by mapping lines.
        
        Returns:
            dict: Source data
        """
```

### 4.5 `services/response_engine.py` — Full Implementation

**Current:** Stub returning `{}`

```python
class ResponseEngine(models.AbstractModel):
    _name = 'connector.response.engine'

    @api.model
    def parse_response(self, context, raw_response):
        """
        Parse HTTP response based on endpoint's parser setting.
        Supports JSON, XML, CSV, TEXT, HTML.
        Also applies RESPONSE mapping if configured.
        
        Returns:
            dict: Parsed and mapped response data
        """
```

### 4.6 `services/auth_engine.py` — Full Implementation

**Current:** Stub returning `{}`

```python
class AuthEngine(models.AbstractModel):
    _name = 'connector.auth.engine'

    @api.model
    def authenticate(self, context):
        """
        Generate authentication using endpoint's auth_method_id.
        Uses connector.auth.method.authenticate() which already
        supports api_key, basic, bearer, jwt, oauth2, hmac, custom.
        
        Returns auth data (headers/query params) and stores in context.
        """
```

### 4.7 `services/compute_engine.py` — Full Implementation

**Current:** Stub returning input

```python
class ComputeEngine(models.AbstractModel):
    _name = 'connector.compute.engine'

    @api.model
    def execute_pipeline(self, value, pipeline_steps, context):
        """
        Execute compute pipeline (sorted by sequence).
        Each step calls connector.compute.function.execute().
        Already implemented in connector.compute.pipeline.execute().
        This engine just orchestrates.
        """
```

### 4.8 `services/execution_engine.py` — Enhance with New Execution Modes

**Current:** Has pipeline structure but all engine calls are stubs.

**Enhancement:** Add new generic execution modes beyond `execute()`.

```python
class ExecutionEngine(models.AbstractModel):
    _name = 'connector.execution.engine'

    # EXISTING (enhance)
    @api.model
    def execute(self, api_code, source_record, environment_code=None, mode='sync'):
        """Enhance: Wire up real engine calls instead of stubs."""

    # NEW — Generic redirect URL builder
    @api.model
    def build_redirect_url(self, api_code, source_record, extra_params=None,
                           environment_code=None):
        """
        Generic: Build a redirect URL for payment gateways.
        
        1. Load config (provider, environment, api, endpoint)
        2. Resolve QUERY mapping to get params dict
        3. Compute hash (sorted query-string style)
        4. Build full URL with hash appended
        5. Log execution
        
        Used by: VNPay pay, MoMo redirect, ZaloPay redirect, etc.
        
        Returns:
            str: Full redirect URL with hash
        """

    # NEW — Generic callback/webhook handler
    @api.model
    def handle_callback(self, provider_code, callback_data, hash_style='sorted_query',
                        exclude_keys=None, hash_key='vnp_SecureHash',
                        secret_setting_code='hash_secret'):
        """
        Generic: Verify and process an incoming callback (IPN/webhook/return).
        
        1. Find provider by code
        2. Get hash secret from settings
        3. Verify hash signature
        4. Return verification result + cleaned data
        
        Used by: VNPay IPN/Return, MoMo callback, ZaloPay callback, etc.
        
        Returns:
            {
                'valid': bool,
                'provider': connector.provider record,
                'data': dict (callback data without hash keys),
                'error': str or None,
            }
        """

    # NEW — Generic server-to-server API call
    @api.model
    def call_api(self, api_code, payload, environment_code=None):
        """
        Generic: Make a server-to-server API call (POST JSON/form).
        
        1. Load config
        2. Build payload from mapping + extra data
        3. Compute hash (pipe-separated or sorted)
        4. Send HTTP POST
        5. Parse response
        6. Log execution
        
        Used by: VNPay querydr/refund, MoMo check-status, etc.
        
        Returns:
            {
                'success': bool,
                'status_code': int,
                'data': dict (parsed response),
                'raw': str,
                'error': str or None,
            }
        """
```

### 4.9 `services/business_engine.py` — Full Implementation

**Current:** Stub returning `{}`

```python
class BusinessEngine(models.AbstractModel):
    _name = 'connector.business.engine'

    @api.model
    def execute_actions(self, context, response_data):
        """
        Execute post-response business actions.
        Looks for connector.plugin records on the provider
        and calls their execute() methods.
        """
```

### 4.10 Model Enhancements

#### `connector.hash.method` — Add hash style field

```python
# NEW field
hash_style = fields.Selection([
    ('sorted_query', 'Sorted Query String'),   # VNPay pay, MoMo, ZaloPay
    ('pipe_separated', 'Pipe Separated'),       # VNPay querydr/refund
    ('json_body', 'JSON Body'),                 # Some REST APIs
    ('custom', 'Custom'),                       # Provider-specific
], string='Hash Style', default='sorted_query')

# NEW field
pipe_fields = fields.Text(
    string='Pipe Fields',
    help='Ordered list of field names for pipe-separated hash (one per line)'
)

# NEW field
exclude_keys = fields.Text(
    string='Exclude Keys',
    help='Keys to exclude from hash computation (one per line, e.g. vnp_SecureHash)'
)

# NEW method
def build_signature(self, params, secret, style=None):
    """
    Generic: Build signature from params using this method's algorithm.
    Dispatches to sorted_query or pipe_separated based on hash_style.
    """

# NEW method
def verify_signature(self, params, received_hash, secret, style=None):
    """
    Generic: Verify a received hash.
    """
```

#### `connector.endpoint` — Add redirect support

```python
# NEW field
execution_type = fields.Selection([
    ('api_call', 'API Call (POST/PUT/PATCH/DELETE)'),
    ('redirect', 'Redirect URL (GET with query params)'),
    ('webhook', 'Webhook Receiver'),
], string='Execution Type', default='api_call')

# NEW field
hash_param_name = fields.Char(
    string='Hash Parameter Name',
    default='vnp_SecureHash',
    help='Name of the hash/signature parameter in the URL or body'
)

# NEW field  
secret_setting_code = fields.Char(
    string='Secret Setting Code',
    default='hash_secret',
    help='Setting code for the hash secret key'
)
```

---

## 5. `dn_payment_vnpay` Module — Mostly Data

### 5.1 Module Structure

```
dn_payment_vnpay/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py                    # IPN + Return URL handlers  
├── models/
│   ├── __init__.py
│   ├── payment_provider.py        # Extend payment.provider with 'vnpay' code
│   └── payment_transaction.py     # VNPay payment URL + notification processing
├── data/
│   ├── vnpay_connector_data.xml   # ALL connector records (provider, env, api, endpoint, mapping, hash)
│   └── vnpay_payment_data.xml     # payment.provider record for Odoo
├── views/
│   ├── payment_provider_views.xml # TMN Code + Hash Secret fields
│   └── payment_vnpay_templates.xml # Redirect form template
├── security/
│   └── ir.model.access.csv
└── static/
    └── description/
        └── icon.png
```

### 5.2 What Goes in `dn_payment_connector_base` vs `dn_payment_vnpay`

| Component | `dn_payment_connector_base` (Generic) | `dn_payment_vnpay` (Data + Custom) |
|-----------|------|------|
| HMAC-SHA512 computation | ✅ `hash_engine.build_sorted_query_hash()` | XML: `connector.hash.method` record |
| Sorted query string builder | ✅ `mapping_engine.build_sorted_params()` | — |
| Pipe-separated hash builder | ✅ `hash_engine.build_pipe_separated_hash()` | XML: `connector.hash.method` record with `pipe_fields` |
| Hash verification | ✅ `hash_engine.verify_hash()` | — |
| Redirect URL builder | ✅ `execution_engine.build_redirect_url()` | — |
| HTTP POST/GET | ✅ `http_engine.send_request()` | — |
| Callback/webhook handler | ✅ `execution_engine.handle_callback()` | — |
| Server-to-server API call | ✅ `execution_engine.call_api()` | — |
| Provider record | ✅ Model | XML: `connector.provider` (code=vnpay) |
| Environments | ✅ Model | XML: sandbox + production |
| Settings (TMN code, secret) | ✅ Model | XML: `connector.setting` records |
| API definitions | ✅ Model | XML: `connector.api` (pay, querydr, refund) |
| Endpoints | ✅ Model | XML: `connector.endpoint` per API per env |
| Parameter mappings | ✅ Model | XML: `connector.mapping` + `connector.mapping.line` |
| Odoo `payment.provider` integration | — | ✅ `payment_provider.py` (add 'vnpay' selection) |
| Payment URL generation for Odoo | — | ✅ `payment_transaction.py` (calls `execution_engine.build_redirect_url()`) |
| IPN/Return controllers | — | ✅ `controllers/main.py` (calls `execution_engine.handle_callback()`) |
| Redirect form template | — | ✅ `payment_vnpay_templates.xml` |

### 5.3 Data Records (XML) — The Core

```xml
<!-- === connector.provider === -->
<record id="connector_provider_vnpay" model="connector.provider">
    <field name="name">VNPay</field>
    <field name="code">vnpay</field>
    <field name="module_name">dn_payment_vnpay</field>
    <field name="version">2.1.0</field>
</record>

<!-- === connector.environment === -->
<record id="env_vnpay_sandbox" model="connector.environment">
    <field name="name">VNPay Sandbox</field>
    <field name="code">sandbox</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
    <field name="base_url">https://sandbox.vnpayment.vn</field>
</record>

<record id="env_vnpay_production" model="connector.environment">
    <field name="name">VNPay Production</field>
    <field name="code">production</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
    <field name="base_url">https://pay.vnpay.vn</field>
    <field name="active" eval="False"/>
</record>

<!-- === connector.setting === -->
<record id="setting_vnpay_tmn_code" model="connector.setting">
    <field name="name">TMN Code</field>
    <field name="code">tmn_code</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
    <field name="value_type">string</field>
    <field name="required" eval="True"/>
</record>

<record id="setting_vnpay_hash_secret" model="connector.setting">
    <field name="name">Hash Secret</field>
    <field name="code">hash_secret</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
    <field name="value_type">password</field>
    <field name="encrypt" eval="True"/>
    <field name="required" eval="True"/>
</record>

<record id="setting_vnpay_version" model="connector.setting">
    <field name="name">API Version</field>
    <field name="code">api_version</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
    <field name="value_type">string</field>
    <field name="value">2.1.0</field>
</record>

<!-- === connector.hash.method === -->
<record id="hash_vnpay_sorted_query" model="connector.hash.method">
    <field name="name">VNPay Payment Hash (Sorted Query)</field>
    <field name="code">vnpay_pay_hash</field>
    <field name="algorithm">hmac_sha512</field>
    <field name="hash_style">sorted_query</field>
    <field name="exclude_keys">vnp_SecureHash
vnp_SecureHashType</field>
</record>

<record id="hash_vnpay_pipe" model="connector.hash.method">
    <field name="name">VNPay QueryDR/Refund Hash (Pipe)</field>
    <field name="code">vnpay_pipe_hash</field>
    <field name="algorithm">hmac_sha512</field>
    <field name="hash_style">pipe_separated</field>
</record>

<!-- === connector.api === -->
<record id="api_vnpay_pay" model="connector.api">
    <field name="name">VNPay Payment</field>
    <field name="code">vnpay_pay</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
    <field name="version">2.1.0</field>
</record>

<record id="api_vnpay_querydr" model="connector.api">
    <field name="name">VNPay Query Transaction</field>
    <field name="code">vnpay_querydr</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
</record>

<record id="api_vnpay_refund" model="connector.api">
    <field name="name">VNPay Refund</field>
    <field name="code">vnpay_refund</field>
    <field name="provider_id" ref="connector_provider_vnpay"/>
</record>

<!-- === connector.endpoint === -->
<record id="endpoint_vnpay_pay_sandbox" model="connector.endpoint">
    <field name="name">Payment Sandbox</field>
    <field name="api_id" ref="api_vnpay_pay"/>
    <field name="environment_id" ref="env_vnpay_sandbox"/>
    <field name="method">GET</field>
    <field name="url">paymentv2/vpcpay.html</field>
    <field name="body_type">NONE</field>
    <field name="execution_type">redirect</field>
    <field name="hash_method_id" ref="hash_vnpay_sorted_query"/>
    <field name="hash_param_name">vnp_SecureHash</field>
    <field name="secret_setting_code">hash_secret</field>
</record>

<record id="endpoint_vnpay_querydr_sandbox" model="connector.endpoint">
    <field name="name">QueryDR Sandbox</field>
    <field name="api_id" ref="api_vnpay_querydr"/>
    <field name="environment_id" ref="env_vnpay_sandbox"/>
    <field name="method">POST</field>
    <field name="url">merchant_webapi/api/transaction</field>
    <field name="body_type">JSON</field>
    <field name="parser">JSON</field>
    <field name="execution_type">api_call</field>
    <field name="hash_method_id" ref="hash_vnpay_pipe"/>
    <field name="hash_param_name">vnp_SecureHash</field>
    <field name="secret_setting_code">hash_secret</field>
</record>

<record id="endpoint_vnpay_refund_sandbox" model="connector.endpoint">
    <field name="name">Refund Sandbox</field>
    <field name="api_id" ref="api_vnpay_refund"/>
    <field name="environment_id" ref="env_vnpay_sandbox"/>
    <field name="method">POST</field>
    <field name="url">merchant_webapi/api/transaction</field>
    <field name="body_type">JSON</field>
    <field name="parser">JSON</field>
    <field name="execution_type">api_call</field>
    <field name="hash_method_id" ref="hash_vnpay_pipe"/>
    <field name="hash_param_name">vnp_SecureHash</field>
    <field name="secret_setting_code">hash_secret</field>
</record>

<!-- === connector.mapping + lines (Payment URL params) === -->
<!-- Each vnp_* parameter is one connector.mapping.line record -->
<!-- Source types: FIXED for constants, SETTING for credentials, FIELD for record data -->
```

### 5.4 Custom Models (Minimal — Only Odoo Integration)

#### `models/payment_provider.py`

```python
class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('vnpay', 'VNPay')],
        ondelete={'vnpay': 'set default'}
    )
    connector_provider_id = fields.Many2one(
        'connector.provider',
        string='Connector Provider',
        compute='_compute_connector_provider_id',
    )

    def _compute_connector_provider_id(self):
        for rec in self:
            if rec.code == 'vnpay':
                rec.connector_provider_id = self.env['connector.provider'].search(
                    [('code', '=', 'vnpay')], limit=1
                )
            else:
                rec.connector_provider_id = False
```

#### `models/payment_transaction.py`

```python
class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """
        Build VNPay redirect URL using dn_payment_connector_base's execution engine.
        Calls: execution_engine.build_redirect_url('vnpay_pay', self)
        """

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Find transaction by vnp_TxnRef."""

    def _process_notification_data(self, notification_data):
        """
        Verify hash using execution_engine.handle_callback().
        Map vnp_ResponseCode to Odoo transaction states.
        """
```

#### `controllers/main.py`

```python
class VNPayController(http.Controller):

    @http.route('/payment/vnpay/return', type='http', auth='public',
                methods=['GET'], csrf=False, save_session=False)
    def vnpay_return(self, **data):
        """Customer redirect from VNPay → process + redirect to /payment/status"""

    @http.route('/payment/vnpay/ipn', type='http', auth='public',
                methods=['GET', 'POST'], csrf=False, save_session=False)
    def vnpay_ipn(self, **data):
        """VNPay server-to-server IPN → verify + update + return JSON"""
```

---

## 6. VNPay Parameter Mappings (XML Data)

### 6.1 Payment URL (vnp_Command=pay)

| VNPay Param | Source Type | Source Path / Value | Compute Pipeline |
|-------------|-----------|---------------------|-----------------|
| `vnp_Version` | FIXED | `2.1.0` | — |
| `vnp_Command` | FIXED | `pay` | — |
| `vnp_TmnCode` | SETTING | `tmn_code` | — |
| `vnp_Amount` | FIELD | `amount` | `multiply(factor=100)` → `floor` |
| `vnp_CurrCode` | FIXED | `VND` | — |
| `vnp_TxnRef` | FIELD | `reference` | — |
| `vnp_OrderInfo` | FIELD | `reference` | `replace(old='', new='Payment ')` |
| `vnp_OrderType` | FIXED | `other` | — |
| `vnp_Locale` | FIXED | `vn` | — |
| `vnp_ReturnUrl` | VARIABLE | `return_url` | — |
| `vnp_IpAddr` | VARIABLE | `ip_addr` | — |
| `vnp_CreateDate` | CONTEXT | `now` | `format_date(format=%Y%m%d%H%M%S)` |
| `vnp_ExpireDate` | CONTEXT | `now` | `add_day(days=0)` → `format_date(...)` |
| `vnp_BankCode` | VARIABLE | `bank_code` | — (optional) |

### 6.2 QueryDR Hash Fields (pipe order)

```
vnp_RequestId | vnp_Version | vnp_Command | vnp_TmnCode | vnp_TxnRef
| vnp_TransactionDate | vnp_CreateDate | vnp_IpAddr | vnp_OrderInfo
```

### 6.3 Refund Hash Fields (pipe order)

```
vnp_RequestId | vnp_Version | vnp_Command | vnp_TmnCode | vnp_TransactionType
| vnp_TxnRef | vnp_Amount | vnp_TransactionNo | vnp_TransactionDate
| vnp_CreateBy | vnp_CreateDate | vnp_IpAddr | vnp_OrderInfo
```

---

## 7. Implementation Sequence

### Step 1: Rename `payment_connector_base` → `dn_payment_connector_base`
- [ ] Rename directory
- [ ] Update `__manifest__.py` (name, asset paths)
- [ ] Update all XML IDs referencing module name
- [ ] Verify module loads

### Step 2: Enhance `dn_payment_connector_base` Models
- [ ] Add `hash_style`, `pipe_fields`, `exclude_keys` to `connector.hash.method`
- [ ] Add `build_signature()` and `verify_signature()` to `connector.hash.method`
- [ ] Add `execution_type`, `hash_param_name`, `secret_setting_code` to `connector.endpoint`
- [ ] Update views for new fields

### Step 3: Implement `dn_payment_connector_base` Service Engines
- [ ] `hash_engine.py` — `build_sorted_query_hash()`, `build_pipe_separated_hash()`, `verify_hash()`
- [ ] `http_engine.py` — `send_request()`, `build_redirect_url()`
- [ ] `mapping_engine.py` — `build_mapping()`, `build_sorted_params()`, `resolve_mapping_for_record()`
- [ ] `load_engine.py` — `load_source_data()`
- [ ] `auth_engine.py` — `authenticate()`
- [ ] `compute_engine.py` — `execute_pipeline()`
- [ ] `response_engine.py` — `parse_response()`
- [ ] `business_engine.py` — `execute_actions()`
- [ ] `execution_engine.py` — Enhance `execute()`, add `build_redirect_url()`, `handle_callback()`, `call_api()`

### Step 4: Create `dn_payment_vnpay` Module
- [ ] Create directory structure
- [ ] `__manifest__.py` (depends: `dn_payment_connector_base`, `payment`)
- [ ] `data/vnpay_connector_data.xml` — all connector records
- [ ] `data/vnpay_payment_data.xml` — Odoo `payment.provider` record
- [ ] `models/payment_provider.py` — add 'vnpay' code
- [ ] `models/payment_transaction.py` — rendering values + notification processing
- [ ] `controllers/main.py` — IPN + Return URL
- [ ] `views/payment_provider_views.xml` — TMN Code, Hash Secret fields
- [ ] `views/payment_vnpay_templates.xml` — redirect form
- [ ] `security/ir.model.access.csv`
- [ ] `static/description/icon.png`

### Step 5: Testing
- [ ] Module installation
- [ ] Hash computation (sorted query + pipe separated)
- [ ] Redirect URL generation
- [ ] IPN callback verification
- [ ] Return URL processing
- [ ] QueryDR API call
- [ ] Refund API call

---

## 8. Future Provider Compatibility

The generic methods added to `dn_payment_connector_base` are designed to work for:

| Future Provider | Redirect URL | Sorted Hash | Pipe Hash | JSON API | Webhook |
|----------------|:---:|:---:|:---:|:---:|:---:|
| **MoMo** | ✅ | ✅ | — | ✅ | ✅ |
| **ZaloPay** | ✅ | ✅ | — | ✅ | ✅ |
| **PayOS** | ✅ | — | — | ✅ | ✅ |
| **GHN Shipping** | — | — | — | ✅ | ✅ |
| **GHTK Shipping** | — | — | — | ✅ | ✅ |
| **E-Invoice** | — | — | — | ✅ | — |

Each new provider only needs:
1. A new Odoo module with **XML data records** (provider, environment, api, endpoint, mapping)
2. Custom controllers for its specific webhook URL patterns
3. Custom model overrides ONLY if its processing logic differs fundamentally

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Hash mismatch with VNPay | Use exact PHP-compatible `urlencode` (space→`+`, not `%20`) |
| VNPay sandbox unreachable | Implement mock mode in base HTTP engine |
| IPN not received on localhost | Document Ngrok/Cloudflare Tunnel requirement |
| Currency not VND | Validate + reject non-VND in payment_transaction |
| Duplicate vnp_TxnRef | Use Odoo's unique reference generator |
| Timezone mismatch | Convert UTC → Asia/Ho_Chi_Minh before formatting dates |
| Base module changes break existing data | Use noupdate=1 for settings, version migration scripts |
