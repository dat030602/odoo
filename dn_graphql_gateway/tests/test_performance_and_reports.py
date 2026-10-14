import requests
import json
import time
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

def run_performance_suite():
    odoo.tools.config.parse_config(["-c", "/opt/odoo19.conf"])
    registry = Registry("odoo19")

    # Retrieve active API Key from dn.graphql.key
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        key_rec = env["dn.graphql.key"].search([("state", "=", "active")], limit=1)
        if not key_rec:
            admin = env.ref("base.user_admin")
            key_rec = env["dn.graphql.key"].create({
                "name": "Benchmark Test Key",
                "user_id": admin.id,
            })
            key_rec.action_generate_key()
            cr.commit()

        api_token = key_rec.raw_key
        key_name = key_rec.name

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    url = "http://localhost:8019/graphql"

    print("======================================================================")
    print("🚀 GRAPHQL GATEWAY PERFORMANCE & REPORT TESTING SUITE")
    print(f"Using API Key: '{key_name}'")
    print("======================================================================\n")

    # -------------------------------------------------------------------------
    # TEST 1: INVENTORY REPORT - stock.picking.picking_type_id.location_src_id.name
    # -------------------------------------------------------------------------
    print("--- [TEST 1] Inventory Movement Report with Deep Nested Relation ---")
    print("Testing path: stock.picking -> picking_type_id -> location_src_id -> name")

    query_stock_nested = """
    query InventoryReportNested($limit: Int) {
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
                display_name
              }
              default_location_src_id {
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
                id
                display_name
              }
              product_uom_qty
              quantity
            }
          }
        }
      }
    }
    """

    t0 = time.time()
    r_stock_10 = requests.post(url, json={"query": query_stock_nested, "variables": {"limit": 10}}, headers=headers)
    dur_stock_10 = (time.time() - t0) * 1000.0

    print(f"Status: {r_stock_10.status_code} in {dur_stock_10:.2f} ms")
    if r_stock_10.status_code == 200:
        data = r_stock_10.json()
        first_node = data["data"]["stock.picking"]["edges"][0]["node"]
        print(f"  Picking: {first_node['name']} (State: {first_node['state']})")
        pt = first_node.get("picking_type_id")
        if pt:
            print(f"  Picking Type: {pt['name']} (Code: {pt['code']})")
            loc_src = pt.get("location_src_id")
            print(f"  >>> picking_type_id.location_src_id.name: {loc_src['name'] if loc_src else 'None'}")
        print(f"  Lines (move_ids) count in first picking: {len(first_node.get('move_ids', []))}")
    else:
        print("ERROR:", r_stock_10.text)

    # -------------------------------------------------------------------------
    # TEST 2: SALES REPORT BY CUSTOMER - sale.order with partner_id & order_line
    # -------------------------------------------------------------------------
    print("\n--- [TEST 2] Sales Report by Customer (Detailed Breakdown) ---")
    query_sales_report = """
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
    """

    t0 = time.time()
    r_sales = requests.post(url, json={
        "query": query_sales_report,
        "variables": {"limit": 20, "domain": "[('state', 'in', ['sale', 'done'])]"}
    }, headers=headers)
    dur_sales = (time.time() - t0) * 1000.0

    print(f"Status: {r_sales.status_code} in {dur_sales:.2f} ms")
    if r_sales.status_code == 200:
        data_sales = r_sales.json()
        total = data_sales["data"]["sale.order"]["totalCount"]
        sample_so = data_sales["data"]["sale.order"]["edges"][0]["node"]
        print(f"  Total Matching Confirmed Orders: {total}")
        print(f"  Sample Order: {sample_so['name']} | Customer: {sample_so['partner_id']['name']} | Total: ${sample_so['amount_total']}")
        print(f"  Number of Order Lines: {len(sample_so['order_line'])}")
    else:
        print("ERROR:", r_sales.text)

    # -------------------------------------------------------------------------
    # TEST 3: BIG DATA BENCHMARK - SCALABILITY & PERFORMANCE (100, 500, 1000 records)
    # -------------------------------------------------------------------------
    print("\n======================================================================")
    print("⚡ BIG QUERY PERFORMANCE BENCHMARK (HIGH VOLUME RESPONSIVENESS)")
    print("======================================================================")

    # Big query on stock.picking with deep nested locations
    query_big_stock = """
    query BigStockReport($first: Int) {
      "stock.picking"(first: $first, order: "id asc") {
        totalCount
        edges {
          node {
            id
            name
            state
            picking_type_id {
              id
              name
              location_src_id {
                name
              }
            }
            location_id {
              name
            }
            location_dest_id {
              name
            }
          }
        }
      }
    }
    """

    for batch_size in [100, 500, 1000]:
        t_start = time.time()
        resp = requests.post(url, json={"query": query_big_stock, "variables": {"first": batch_size}}, headers=headers)
        elapsed_ms = (time.time() - t_start) * 1000.0
        payload_kb = len(resp.content) / 1024.0

        if resp.status_code == 200:
            rec_count = len(resp.json()["data"]["stock.picking"]["edges"])
            print(f"  [Batch {batch_size:4d} Pickings] -> HTTP {resp.status_code} | Retrieved: {rec_count:4d} records | Response Size: {payload_kb:6.1f} KB | Latency: {elapsed_ms:7.2f} ms")
        else:
            print(f"  [Batch {batch_size:4d} Pickings] -> FAILED {resp.status_code}: {resp.text[:200]}")

    # Big query on sale.order with order_line and partner
    print("\n--- Big Query Benchmark on Sale Orders (500 records with lines) ---")
    query_big_sales = """
    query BigSalesReport($first: Int) {
      "sale.order"(first: $first, order: "id asc") {
        totalCount
        edges {
          node {
            id
            name
            partner_id {
              name
            }
            amount_total
            order_line {
              id
              product_uom_qty
              price_subtotal
            }
          }
        }
      }
    }
    """
    for batch_size in [100, 500]:
        t_start = time.time()
        resp = requests.post(url, json={"query": query_big_sales, "variables": {"first": batch_size}}, headers=headers)
        elapsed_ms = (time.time() - t_start) * 1000.0
        payload_kb = len(resp.content) / 1024.0

        if resp.status_code == 200:
            rec_count = len(resp.json()["data"]["sale.order"]["edges"])
            print(f"  [Batch {batch_size:4d} Orders]   -> HTTP {resp.status_code} | Retrieved: {rec_count:4d} records | Response Size: {payload_kb:6.1f} KB | Latency: {elapsed_ms:7.2f} ms")
        else:
            print(f"  [Batch {batch_size:4d} Orders]   -> FAILED {resp.status_code}: {resp.text[:200]}")

    print("\n======================================================================")
    print("✅ BENCHMARK COMPLETE")
    print("======================================================================")

if __name__ == "__main__":
    run_performance_suite()
