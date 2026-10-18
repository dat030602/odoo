import json
import logging
import re
import time
import uuid
from datetime import datetime

import odoo
from odoo import http
from odoo.http import request
from graphql import parse, specified_rules, validate, graphql_sync, GraphQLError
from graphql.language.ast import OperationDefinitionNode, OperationType

from ..core.errors import (
    AuthenticationError,
    KeyExpiredError,
    ForbiddenResourceError,
    UploadNotAllowedError,
    RateLimitExceededError,
    SavepointRollbackTrigger,
    format_error_payload,
)
from ..core.lexer_rewriter import rewrite_quoted_names, restore_names
from ..core.rules import DenyChecker, DenyListValidationRule, calculate_query_depth
from ..core.schema_builder import get_schema
from ..models.graphql_rate_limit import DnGraphqlRateLimit
from ..models.graphql_log import DnGraphqlLog

_logger = logging.getLogger(__name__)


def mask_sensitive_data(text_val: str) -> str:
    """Masks credentials, passwords, tokens and secret values in query/variables text."""
    if not text_val:
        return ""
    # Mask password fields
    pattern = r'("?(?:password|token|secret|newKey)"?\s*:\s*)"([^"]+)"'
    masked = re.sub(pattern, r'\1"***MASKED***"', text_val, flags=re.IGNORECASE)
    return masked


class GraphQLController(http.Controller):

    @http.route('/graphql', type='http', auth='none', methods=['POST'], csrf=False, readonly=False)
    def graphql_endpoint(self, **kw):
        started_at = time.time()
        request_id = str(uuid.uuid4())
        raw_key = None
        key_record = None
        gw_key_id = False
        user_id = None
        operation_name = None
        raw_query = ""
        variables = {}
        payload = {}
        status_code = 200
        error_code = None
        error_msg = None
        node_count = 0
        rolled_back = False
        db_name = None
        request_body_str = ""
        response_body_str = ""

        try:
            body_bytes = request.httprequest.data
            request_body_str = body_bytes.decode('utf-8', errors='replace') if body_bytes else ''
        except Exception:
            request_body_str = ''

        def make_resp(payload_dict, code=200):
            nonlocal response_body_str, status_code
            status_code = code
            try:
                response_body_str = json.dumps(payload_dict, indent=2, ensure_ascii=False, default=str)
            except Exception:
                response_body_str = str(payload_dict)
            return request.make_json_response(payload_dict, status=code)

        try:
            # 1. Determine Database
            # In auth='none', resolve database from session or host
            if not request.db:
                request.session.db = odoo.tools.config.get('db_name') or 'odoo19'
            db_name = request.db or 'odoo19'

            # 2. Upload Check: Strictly prohibit multipart/form-data file uploads
            content_type = request.httprequest.content_type or ''
            if 'multipart/form-data' in content_type:
                raise UploadNotAllowedError("File uploads via multipart/form-data are strictly forbidden on this endpoint.")

            # 3. Authentication: Bearer token from Authorization header
            auth_header = request.httprequest.headers.get('Authorization', '').strip()
            if not auth_header.startswith('Bearer '):
                raise AuthenticationError("Missing or malformed Authorization header. Bearer API key required.")

            raw_key = auth_header[7:].strip()
            if not raw_key:
                raise AuthenticationError("Empty Bearer API key provided.")

            # Look up API key record and check credentials using request.env.cr
            from odoo.addons.base.models.res_users import KEY_CRYPT_CONTEXT

            cr = request.env.cr
            index = raw_key[:8]
            cr.execute("""
                SELECT id, user_id, expiration_date, key
                FROM res_users_apikeys
                WHERE index = %s AND (scope IS NULL OR scope = 'graphql')
            """, (index,))
            rows = cr.fetchall()

            matched_row = None
            for kid, kuid, kexp, khash in rows:
                if KEY_CRYPT_CONTEXT.verify(raw_key, khash):
                    matched_row = (kid, kuid, kexp)
                    break

            if not matched_row:
                raise AuthenticationError("Invalid API key or insufficient scope.")

            key_id, user_id, expiration_date = matched_row
            if expiration_date and expiration_date < datetime.utcnow():
                raise KeyExpiredError("The provided API key has expired.")

            # Look up dn.graphql.key record if any
            try:
                cr.execute("SELECT id FROM dn_graphql_key WHERE key_id = %s LIMIT 1", (key_id,))
                gw_row = cr.fetchone()
                if gw_row:
                    gw_key_id = gw_row[0]
            except Exception:
                pass

            # Check rate limit (default 60 requests/min)
            limit_min = int(request.env['ir.config_parameter'].sudo().get_param('dn_graphql_gateway.rate_limit_minute', 60))
            if not DnGraphqlRateLimit.check_and_increment(cr, index, limit_min):
                raise RateLimitExceededError(f"Rate limit exceeded (maximum {limit_min} requests per minute).")

            # 4. Update request environment to the authenticated user
            request.update_env(user=user_id)
            key_record = request.env['res.users.apikeys'].sudo().browse(key_id)

            # 5. Parse JSON request body
            try:
                payload = json.loads(request_body_str) if request_body_str else {}
            except Exception as e:
                return make_resp(
                    format_error_payload(f"Malformed JSON body: {e}", code='GRAPHQL_VALIDATION_FAILED', request_id=request_id),
                    code=400
                )

            raw_query = payload.get('query', '')
            variables = payload.get('variables', {}) or {}
            operation_name = payload.get('operationName')

            if not raw_query:
                return make_resp(
                    format_error_payload("GraphQL query string cannot be empty.", code='GRAPHQL_VALIDATION_FAILED', request_id=request_id),
                    code=400
                )

            # 6. Pre-process quoted model identifiers ("sale.order" -> sale__order)
            rewritten_query, name_mapping = rewrite_quoted_names(raw_query)

            # 7. AST Parse & Depth Validation
            try:
                document = parse(rewritten_query)
            except Exception as e:
                return make_resp(
                    format_error_payload(f"Syntax error in query: {e}", code='GRAPHQL_VALIDATION_FAILED', request_id=request_id),
                    code=400
                )

            max_depth = int(request.env['ir.config_parameter'].sudo().get_param('dn_graphql_gateway.max_depth', 12))
            query_depth = calculate_query_depth(document)
            if query_depth > max_depth:
                return make_resp(
                    format_error_payload(f"Query depth {query_depth} exceeds configured limit of {max_depth}.", code='GRAPHQL_VALIDATION_FAILED', request_id=request_id),
                    code=400
                )

            # 8. Deny List Enforcement via AST Validation Rules
            deny_checker = DenyChecker(request.env, key_rec_id=gw_key_id, api_key_id=key_id)
            schema = get_schema(request.env)

            validation_errors = validate(schema, document, rules=list(specified_rules) + [lambda ctx: DenyListValidationRule(ctx, deny_checker)])
            if validation_errors:
                first_err = validation_errors[0]
                err_code = getattr(first_err, 'extensions', {}).get('code', 'GRAPHQL_VALIDATION_FAILED')
                status_code = 403 if err_code == 'FORBIDDEN_RESOURCE' else 400
                error_dict = {
                    'message': first_err.message,
                    'extensions': {'code': err_code, 'requestId': request_id}
                }
                return make_resp({'data': None, 'errors': [error_dict]}, code=status_code)

            # 9. Execution Context & Atomic Mutation Savepoint
            # Determine if this operation is a Mutation
            is_mutation = False
            for defn in document.definitions:
                if isinstance(defn, OperationDefinitionNode) and defn.operation == OperationType.MUTATION:
                    is_mutation = True
                    break

            context_val = {
                'env': request.env,
                'request': request,
                'api_key_record': key_record,
                'raw_key': raw_key,
                'deny_checker': deny_checker,
                'node_count': 0,
            }

            if is_mutation:
                # Wrap entire mutation in a database savepoint
                try:
                    with request.env.cr.savepoint():
                        res = graphql_sync(
                            schema,
                            rewritten_query,
                            variable_values=variables,
                            operation_name=operation_name,
                            context_value=context_val
                        )
                        # Check for execution errors or business userErrors
                        has_error = bool(res.errors)
                        if not has_error and res.data:
                            for val in res.data.values():
                                if isinstance(val, dict) and val.get('userErrors'):
                                    has_error = True
                                    break
                        if has_error:
                            raise SavepointRollbackTrigger(res.errors)
                except SavepointRollbackTrigger:
                    rolled_back = True
            else:
                res = graphql_sync(
                    schema,
                    rewritten_query,
                    variable_values=variables,
                    operation_name=operation_name,
                    context_value=context_val
                )

            node_count = context_val.get('node_count', 0)

            # 10. Format and Restore Quoted Names in Response
            response_payload = {}
            if res.data is not None:
                response_payload['data'] = restore_names(res.data, name_mapping)
            else:
                response_payload['data'] = None

            if res.errors:
                formatted_errors = []
                for e in res.errors:
                    err_item = {
                        'message': e.message,
                        'extensions': getattr(e, 'extensions', {}) or {'code': 'INTERNAL_SERVER_ERROR'}
                    }
                    if e.path:
                        err_item['path'] = restore_names(list(e.path), name_mapping)
                    err_item['extensions']['requestId'] = request_id
                    formatted_errors.append(err_item)
                response_payload['errors'] = formatted_errors

            if rolled_back:
                response_payload['extensions'] = {'rolledBack': True, 'requestId': request_id}

            return make_resp(response_payload, code=200)

        except AuthenticationError as e:
            error_code = e.code
            error_msg = e.message
            return make_resp(format_error_payload(e.message, code=e.code, request_id=request_id), code=401)
        except KeyExpiredError as e:
            error_code = e.code
            error_msg = e.message
            return make_resp(format_error_payload(e.message, code=e.code, request_id=request_id), code=401)
        except ForbiddenResourceError as e:
            error_code = e.code
            error_msg = e.message
            return make_resp(format_error_payload(e.message, code=e.code, request_id=request_id), code=403)
        except UploadNotAllowedError as e:
            error_code = e.code
            error_msg = e.message
            return make_resp(format_error_payload(e.message, code=e.code, request_id=request_id), code=415)
        except RateLimitExceededError as e:
            error_code = e.code
            error_msg = e.message
            return make_resp(format_error_payload(e.message, code=e.code, request_id=request_id), code=429)
        except Exception as e:
            _logger.exception("Unhandled error in GraphQL endpoint: %s", e)
            error_code = 'INTERNAL_SERVER_ERROR'
            error_msg = str(e)
            return make_resp(format_error_payload("An unexpected internal server error occurred.", code='INTERNAL_SERVER_ERROR', request_id=request_id), code=500)
        finally:
            # 11. Write Audit Log using isolated database cursor
            try:
                duration_ms = (time.time() - started_at) * 1000.0
                masked_query = mask_sensitive_data(raw_query)
                masked_vars = mask_sensitive_data(json.dumps(variables, indent=2, ensure_ascii=False, default=str) if variables else "")

                if payload:
                    formatted_req = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
                else:
                    try:
                        formatted_req = json.dumps(json.loads(request_body_str), indent=2, ensure_ascii=False, default=str) if request_body_str else ""
                    except Exception:
                        formatted_req = request_body_str

                masked_req = mask_sensitive_data(formatted_req)
                masked_resp = mask_sensitive_data(response_body_str)
                log_vals = {
                    'request_id': request_id,
                    'key_rec_id': gw_key_id or False,
                    'api_key_name': (raw_key[:8] + '...') if raw_key else 'n/a',
                    'user_id': user_id or False,
                    'ip_address': request.httprequest.remote_addr or 'n/a',
                    'operation_name': operation_name or 'unnamed',
                    'query_text': masked_query,
                    'variables_text': masked_vars,
                    'request_body': masked_req,
                    'response_body': masked_resp,
                    'status_code': status_code,
                    'duration_ms': round(duration_ms, 2),
                    'error_code': error_code,
                    'error_message': error_msg,
                    'node_count': node_count,
                    'rolled_back': rolled_back,
                }
                DnGraphqlLog.log_request_isolated(request.env, log_vals)
            except Exception as log_ex:
                _logger.warning("Failed to commit GraphQL log: %s", log_ex)

    @http.route('/graphql/docs', type='http', auth='none', methods=['GET'], csrf=False)
    def graphql_docs(self, **kw):
        """Interactive GraphiQL / GraphQL Gateway Documentation page."""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>GraphQL API Gateway for Odoo</title>
    <meta charset="utf-8" />
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px 40px; background: #0f172a; color: #f8fafc; line-height: 1.6; }
        h1, h2, h3 { color: #38bdf8; margin-top: 0; }
        h3 { color: #7dd3fc; margin-top: 16px; margin-bottom: 8px; }
        pre, code { background: #1e293b; color: #a5f3fc; padding: 4px 8px; border-radius: 4px; font-family: "JetBrains Mono", Consolas, monospace; }
        pre { padding: 16px; overflow-x: auto; border: 1px solid #334155; position: relative; margin: 8px 0 16px 0; border-radius: 6px; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: bold; background: #0284c7; color: white; margin-right: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { border: 1px solid #334155; padding: 10px 14px; text-align: left; }
        th { background: #0f172a; color: #38bdf8; }
        .copy-btn { position: absolute; top: 8px; right: 8px; background: #334155; color: #94a3b8; border: 1px solid #475569; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-family: inherit; transition: all 0.2s; }
        .copy-btn:hover { background: #0284c7; color: #ffffff; border-color: #0284c7; }
        .tag-curl { background: #059669; color: #ecfdf5; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
        .tag-gql { background: #7c3aed; color: #ede9fe; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
    </style>
    <script>
        function copyCode(btn) {
            const pre = btn.closest('pre');
            const codeEl = pre.querySelector('code');
            const textToCopy = (codeEl ? codeEl.innerText : pre.innerText).replace('Copy', '').trim();
            navigator.clipboard.writeText(textToCopy).then(() => {
                const origText = btn.innerText;
                btn.innerText = '✓ Copied!';
                btn.style.background = '#10b981';
                btn.style.color = '#ffffff';
                setTimeout(() => {
                    btn.innerText = origText;
                    btn.style.background = '';
                    btn.style.color = '';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        }
    </script>
</head>
<body>
    <h1>🚀 GraphQL API Gateway for Odoo 19</h1>
    <p>High-performance GraphQL endpoint with native Odoo ACL, Record Rules, Atomic Savepoint Rollback, and Security Blocklist.</p>

    <div class="card">
        <h2>📌 Endpoint Specifications</h2>
        <table>
            <tr><th>HTTP URL</th><td><code>POST http://localhost:8019/graphql</code> (or your domain endpoint)</td></tr>
            <tr><th>Documentation</th><td><code>GET /graphql/docs</code></td></tr>
            <tr><th>Authentication</th><td><code>Authorization: Bearer &lt;API_KEY&gt;</code> (Manage keys via menu: <b>GraphQL Gateway &gt; API Keys</b>)</td></tr>
            <tr><th>Content-Type</th><td><code>application/json</code> (Binary uploads strictly prohibited)</td></tr>
        </table>
    </div>

    <div class="card">
        <h2>💻 Sample cURL Commands (Copy &amp; Paste Ready)</h2>
        <p>Replace <code>&lt;YOUR_API_KEY&gt;</code> with your token from <b>GraphQL Gateway &gt; API Keys Management</b>.</p>

        <h3>1. Query Records with Domain Filter</h3>
        <span class="tag-curl">cURL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>curl -X POST http://localhost:8019/graphql \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer &lt;YOUR_API_KEY&gt;" \\
  -d '{
    "query": "query GetDoneMoves($domain: String!) { stock__move(first: 5, domain: $domain, order: \\"date desc\\") { totalCount pageInfo { hasNextPage endCursor } edges { node { id reference quantity_done location_id { name } location_dest_id { name } } } } }",
    "variables": {
      "domain": "[(\\"state\\", \\"=\\", \\"done\\")]"
    }
  }'</code></pre>

        <h3>2. Create a Record (Mutation)</h3>
        <span class="tag-curl">cURL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>curl -X POST http://localhost:8019/graphql \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer &lt;YOUR_API_KEY&gt;" \\
  -d '{
    "query": "mutation CreatePartner($values: ResPartnerInput!) { res__partner__create(values: $values) { node { id name email } userErrors { message field code } } }",
    "variables": {
      "values": {
        "name": "ZZTEST_Agro_Supplier",
        "email": "contact@agro.com"
      }
    }
  }'</code></pre>

        <h3>3. Invoke Business Method / Action (callMethod)</h3>
        <span class="tag-curl">cURL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>curl -X POST http://localhost:8019/graphql \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer &lt;YOUR_API_KEY&gt;" \\
  -d '{
    "query": "mutation ConfirmSaleOrder($model: String!, $method: String!, $id: Int!) { callMethod(model: $model, method: $method, id: $id) { success result userErrors { message field code } } }",
    "variables": {
      "model": "sale.order",
      "method": "action_confirm",
      "id": 42
    }
  }'</code></pre>

        <h3>4. Inventory In-Out-Balance Report (Stock Card)</h3>
        <span class="tag-curl">cURL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>curl -X POST http://localhost:8019/graphql \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer &lt;YOUR_API_KEY&gt;" \\
  -d '{
    "query": "mutation GetStockReport($model: String!, $method: String!, $kwargs: String!) { callMethod(model: $model, method: $method, kwargs: $kwargs) { success result userErrors { message field code } } }",
    "variables": {
      "model": "dn.graphql.stock.report",
      "method": "action_bao_cao_xuat_nhap_ton",
      "kwargs": "{\\"product_id\\": 1764, \\"location_id\\": 5, \\"date_from\\": \\"2026-01-01 00:00:00\\", \\"date_to\\": \\"2026-12-31 23:59:59\\", \\"states\\": [\\"done\\"]}"
    }
  }'</code></pre>

        <h3>5. Rotate Current API Key</h3>
        <span class="tag-curl">cURL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>curl -X POST http://localhost:8019/graphql \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer &lt;YOUR_CURRENT_API_KEY&gt;" \\
  -d '{
    "query": "mutation { rotateApiKey(expiresInDays: 60) { newKey expirationDate userErrors { message code } } }"
  }'</code></pre>
    </div>

    <div class="card">
        <h2>💡 Sample Query (GraphQL Syntax)</h2>
        <span class="tag-gql">GraphQL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>query GetPartners {
  res__partner(first: 5, order: "id desc") {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      cursor
      node {
        id
        name
        email
      }
    }
  }
}</code></pre>
    </div>

    <div class="card">
        <h2>⚡ Sample Mutation (Atomic Savepoint Rollback)</h2>
        <span class="tag-gql">GraphQL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>mutation CreatePartner {
  res__partner__create(values: { name: "ZZTEST_Global Agro Supplies", email: "info@agro.com" }) {
    node {
      id
      name
    }
    userErrors {
      message
      field
      code
    }
  }
}</code></pre>
    </div>

    <div class="card">
        <h2>⚙️ Calling Business Methods (Actions &amp; Custom Workflows)</h2>
        <p>Invoke public model or recordset methods (e.g. <code>action_confirm</code>, <code>button_validate</code>, <code>action_cancel</code>) directly:</p>
        
        <span class="tag-gql">GraphQL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code># Example 1: Generic callMethod syntax
mutation ConfirmPurchaseOrder {
  callMethod(model: "purchase.order", id: 15, method: "button_confirm") {
    success
    result
    userErrors {
      message
      field
      code
    }
  }
}

# Example 2: Calling on multiple records with optional JSON kwargs
mutation AssignPickings {
  callMethod(model: "stock.picking", ids: [101, 102], method: "action_assign", kwargs: "{}") {
    success
    result
    userErrors {
      message
    }
  }
}

# Example 3: Model-bound helper mutation
mutation CallSaleOrderMethod {
  sale__order__call(id: 42, method: "action_confirm") {
    success
    result
    userErrors {
      message
    }
  }
}</code></pre>
    </div>

    <div class="card">
        <h2>📊 Reporting &amp; Deep Relational Queries</h2>
        <p>GraphQL Gateway supports multi-level relational queries with automatic prefetch optimization:</p>
        
        <h3>1. Inventory Movement Report (Deep Locations: stock__picking &rarr; picking_type_id &rarr; location_src_id)</h3>
        <span class="tag-gql">GraphQL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>query InventoryMovementReport($limit: Int) {
  stock__picking(first: $limit, order: "id desc") {
    totalCount
    edges {
      node {
        id
        name
        state
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
          name
        }
        location_dest_id {
          name
        }
        move_ids {
          id
          product_id {
            display_name
          }
          quantity
        }
      }
    }
  }
}</code></pre>

        <h3>2. Sales Report by Customer (Detailed Order Lines Breakdown)</h3>
        <span class="tag-gql">GraphQL</span>
        <pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code>query SalesReportByCustomer($limit: Int) {
  sale__order(first: $limit, domain: "[('state', 'in', ['sale', 'done'])]", order: "date_order desc") {
    totalCount
    edges {
      node {
        id
        name
        date_order
        partner_id {
          id
          name
          email
          phone
        }
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
}</code></pre>
    </div>
</body>
</html>"""
        return request.make_response(html_content, headers=[('Content-Type', 'text/html')])
