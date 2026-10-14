import requests
import json
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID
from datetime import datetime, timedelta

def main():
    odoo.tools.config.parse_config(["-c", "/opt/odoo19.conf"])
    registry = Registry("odoo19")

    # 1. Create Users & API Keys inside Odoo transaction
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # User 1: Sales Service User
        sales_group = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False) or env.ref("base.group_user")
        user_sales = env["res.users"].search([("login", "=", "sales_api_user")], limit=1)
        if not user_sales:
            user_sales = env["res.users"].create({
                "name": "Sales API Service User",
                "login": "sales_api_user",
                "email": "sales_api@example.com",
                "group_ids": [(6, 0, [env.ref("base.group_user").id, sales_group.id])],
            })

        key_sales = env["dn.graphql.key"].search([("user_id", "=", user_sales.id), ("state", "=", "active")], limit=1)
        if not key_sales:
            key_sales = env["dn.graphql.key"].create({
                "name": "Sales Integration Key (Mobile App)",
                "user_id": user_sales.id,
                "expiration_date": datetime.utcnow() + timedelta(days=90),
            })
            key_sales.action_generate_key()

        sales_token = key_sales.raw_key
        sales_key_id = key_sales.id
        sales_index = key_sales.key_index

        # User 2: Warehouse Service User
        stock_group = env.ref("stock.group_stock_user", raise_if_not_found=False) or env.ref("base.group_user")
        user_stock = env["res.users"].search([("login", "=", "warehouse_api_user")], limit=1)
        if not user_stock:
            user_stock = env["res.users"].create({
                "name": "Warehouse Scanner Service User",
                "login": "warehouse_api_user",
                "email": "warehouse_api@example.com",
                "group_ids": [(6, 0, [env.ref("base.group_user").id, stock_group.id])],
            })

        key_stock = env["dn.graphql.key"].search([("user_id", "=", user_stock.id), ("state", "=", "active")], limit=1)
        if not key_stock:
            key_stock = env["dn.graphql.key"].create({
                "name": "Warehouse Scanner Integration Key",
                "user_id": user_stock.id,
                "expiration_date": datetime.utcnow() + timedelta(days=60),
            })
            key_stock.action_generate_key()

        stock_token = key_stock.raw_key
        stock_key_id = key_stock.id
        stock_index = key_stock.key_index

        cr.commit()

    print(f"[OK] Sales Key: ID={sales_key_id}, Index={sales_index}")
    print(f"[OK] Warehouse Key: ID={stock_key_id}, Index={stock_index}")

    # 2. Execute Live HTTP Requests
    # Request 1: Sales query
    headers_sales = {"Authorization": f"Bearer {sales_token}", "Content-Type": "application/json"}
    body_sales = {
        "query": 'query GetPartners($limit: Int) { "res.partner"(first: $limit) { totalCount edges { node { id name } } } }',
        "variables": {"limit": 2},
        "operationName": "GetPartners"
    }
    r1 = requests.post("http://localhost:8019/graphql", json=body_sales, headers=headers_sales)
    print("\n--- Test 1 (Sales Query) ---")
    print("HTTP Status:", r1.status_code)
    print("Response Data:", json.dumps(r1.json(), indent=2))

    # Request 2: Warehouse query
    headers_stock = {"Authorization": f"Bearer {stock_token}", "Content-Type": "application/json"}
    body_stock = {
        "query": 'query GetStockPickings { "stock.picking"(first: 2) { totalCount edges { node { id name state } } } }',
        "variables": {},
        "operationName": "GetStockPickings"
    }
    r2 = requests.post("http://localhost:8019/graphql", json=body_stock, headers=headers_stock)
    print("\n--- Test 2 (Warehouse Query) ---")
    print("HTTP Status:", r2.status_code)
    print("Response Data:", json.dumps(r2.json(), indent=2))

    # Request 3: Business method call using Sales Key
    body_call = {
        "query": 'mutation CheckPartnerAccess($id: Int!, $method: String!, $args: String) { "res.partner.call"(id: $id, method: $method, args: $args) { success result userErrors { message code } } }',
        "variables": {"id": 1, "method": "check_access_rights", "args": json.dumps(["read"])},
        "operationName": "CheckPartnerAccess"
    }
    r3 = requests.post("http://localhost:8019/graphql", json=body_call, headers=headers_sales)
    print("\n--- Test 3 (Business Method Call) ---")
    print("HTTP Status:", r3.status_code)
    print("Response Data:", json.dumps(r3.json(), indent=2))

    # 3. Verify Database Audit Logs
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        k_sales = env["dn.graphql.key"].browse(sales_key_id)
        k_stock = env["dn.graphql.key"].browse(stock_key_id)

        print("\n========================================================")
        print("=== AUDIT LOGS VERIFICATION IN DATABASE (dn.graphql.log) ===")
        print("========================================================")
        print(f"Sales Key Record: '{k_sales.name}' (User: {k_sales.user_id.name})")
        print(f"-> Total Requests Logged: {k_sales.log_count}")
        for idx, log in enumerate(k_sales.log_ids[:3], 1):
            print(f"\n  [Sales Log #{idx}]")
            print(f"  - Request UUID: {log.request_id}")
            print(f"  - Operation: {log.operation_name}")
            print(f"  - Status Code: {log.status_code}")
            print(f"  - Duration: {log.duration_ms} ms")
            print(f"  - Request Body: {log.request_body}")
            print(f"  - Response Body: {log.response_body}")

        print(f"\nWarehouse Key Record: '{k_stock.name}' (User: {k_stock.user_id.name})")
        print(f"-> Total Requests Logged: {k_stock.log_count}")
        for idx, log in enumerate(k_stock.log_ids[:3], 1):
            print(f"\n  [Warehouse Log #{idx}]")
            print(f"  - Request UUID: {log.request_id}")
            print(f"  - Operation: {log.operation_name}")
            print(f"  - Status Code: {log.status_code}")
            print(f"  - Duration: {log.duration_ms} ms")
            print(f"  - Request Body: {log.request_body}")
            print(f"  - Response Body: {log.response_body}")

if __name__ == "__main__":
    main()
