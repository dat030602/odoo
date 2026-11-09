# Odoo 20 Controller Guide

## Coding Conventions

- Use `type='jsonrpc'` for JSON-RPC endpoints (`type='json'` is a deprecated alias).
- Always specify explicit `auth=` (`'user'`, `'public'`, or `'none'`).
- Use object-based GeoIP properties (`request.geoip.city`, `request.geoip.country_name`) rather than dictionary access.
- Always validate input parameters and avoid trusting raw client data.
- Return structured dictionaries for `type='jsonrpc'` and `request.render()` or `request.make_response()` for `type='http'`.

---

## Table of Contents

- [Controllers Overview](#controllers-overview)
- [Route Definition & Authentication](#route-definition--authentication)
- [JSON-RPC Controllers](#json-rpc-controllers)
- [HTTP Controllers & Web Pages](#http-controllers--web-pages)
- [GeoIP API in Odoo 20](#geoip-api-in-odoo-20)
- [Security & CSRF Protection](#security--csrf-protection)

---

## Controllers Overview

Controllers handle incoming HTTP and JSON-RPC web requests.

```python
from odoo import http
from odoo.http import request

class MyController(http.Controller):
    @http.route('/my_module/ping', type='jsonrpc', auth='public')
    def ping(self):
        return {'status': 'ok'}
```

---

## Route Definition & Authentication

### Route Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `route` | str/list | Path or list of paths |
| `type` | str | `'jsonrpc'` (standard JSON-RPC) or `'http'` (raw HTTP) |
| `auth` | str | `'user'` (logged in), `'public'` (portal/visitor), `'none'` (no environment) |
| `methods` | list[str] | Allowed HTTP methods (`['GET', 'POST']`) |
| `cors` | str | Cross-origin resource sharing header |
| `csrf` | bool | Enforce CSRF token check (default `True` for HTTP POST) |

---

## JSON-RPC Controllers

JSON-RPC 2.0 endpoints receive parameters as JSON and return Python data structures automatically serialized to JSON:

```python
from odoo import http
from odoo.http import request

class TaskApiController(http.Controller):

    @http.route('/api/v1/task/create', type='jsonrpc', auth='user', methods=['POST'])
    def create_task(self, title, deadline=None, priority='0'):
        if not title:
            return {'error': 'Title is required'}

        task = request.env['project.task'].create({
            'name': title,
            'date_deadline': deadline,
            'priority': priority,
            'user_id': request.env.uid,
        })
        return {
            'success': True,
            'task_id': task.id,
            'task_name': task.name,
        }
```

---

## External API in Odoo 20 (`/json/2` vs XML-RPC)

- **Legacy XML-RPC / JSON-RPC**:
  - The `db` service has been **completely removed** (`/xmlrpc/2/db` raises `ValueError: Invalid service name: db`).
  - The `common` and `object` services (`/xmlrpc/2/common`, `/xmlrpc/2/object`) remain operational for backwards compatibility, but log deprecation notices and are scheduled for removal in Odoo 22.
- **Modern External API: `/json/2`**:
  - Located in `addons/rpc/controllers/json2.py`.
  - Format: `POST /json/2/<model>/<method>`
  - Uses modern authentication and returns native JSON with HTTP error codes.

---

## HTTP Controllers & Web Pages

```python
class PortalTaskController(http.Controller):

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_tasks(self, page=1, **kw):
        Task = request.env['project.task']
        tasks = Task.search([('user_id', '=', request.env.uid)])

        return request.render('my_module.portal_my_tasks_template', {
            'tasks': tasks,
            'page_name': 'tasks',
        })
```

---

## GeoIP API in Odoo 20

> **Odoo 20 Deprecation**: Dictionary access on `request.geoip` (e.g. `request.geoip['country_code']`) is deprecated. Use direct object attributes:

```python
@http.route('/my_module/location', type='jsonrpc', auth='public')
def get_location(self):
    geoip = request.geoip
    return {
        'country_code': geoip.country_code or 'US',
        'country_name': geoip.country_name or 'United States',
        'city': geoip.city or 'Unknown',
        'latitude': geoip.latitude,
        'longitude': geoip.longitude,
    }
```

---

## Security & CSRF Protection

1. **CSRF Tokens**:
   Never disable CSRF (`csrf=False`) on web forms or user-triggered POST routes unless developing a public webhook intended for third-party systems.
2. **Access Rights**:
   Remember that `request.env` runs with the permissions of the authenticated user (`request.env.user`). Always check access rights before performing privileged operations:
   ```python
   task = request.env['project.task'].browse(task_id)
   task.check_access('write')
   ```

