# -*- coding: utf-8 -*-
{
    "name": "Vietnam Address NQ60 Connector Integration (v2)",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "summary": "Synchronizes Vietnam Administrative Divisions NQ60 v2 via Universal REST Connector Framework Inbox",
    "description": """
Vietnam Address NQ60 Connector Integration (v2)
===============================================
Bridges the Vietnam Administrative Reform (NQ60 v2: 34 Provinces, 3,321 Wards)
with `dn_connector_base` transactional Inbox and queue processing.

Features:
- Connector Framework Preset (`vn_address_v2`).
- Inbound Gateway Endpoint with Python handler for 2-tier NQ60 data ingestion.
- Maps consolidated wards (`is_new=True`) and legacy merger references (`map_with_ward_ids`).
- Seeds real Vietnam NQ60 address records on database `odoo19`.
""",
    "author": 'Dyan',
    'images': ['static/description/banner.png'],
    "license": "LGPL-3",
    "depends": ["base", "dn_connector_base", "dn_vn_address_nq60"],
    "data": [
        "security/ir.model.access.csv",
        "data/connector_framework_data.xml",
        "data/connector_inbound_endpoint_data.xml",
        "data/seed_real_data_v2.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
