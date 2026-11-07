# -*- coding: utf-8 -*-
{
    "name": "Vietnam Address Connector Integration (v1)",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "summary": "Synchronizes Vietnam Administrative Divisions v1 via Universal REST Connector Framework Inbox",
    "description": """
Vietnam Address Connector Integration (v1)
==========================================
Bridges the Vietnam Administrative Address (v1) data structures with `dn_connector_base`.

Features:
- Connector Framework Preset (`vn_address_v1`).
- Inbound Gateway Endpoint with Python safe_eval batch handler.
- Asynchronous FIFO queueing and transactional Inbox processing.
- Seeds real Vietnam address records (Hanoi, Da Nang, Ho Chi Minh) via connector inbox.
""",
    "author": "MJB Solutions",
    "license": "LGPL-3",
    "depends": ["base", "dn_connector_base", "dn_vn_address"],
    "data": [
        "security/ir.model.access.csv",
        "data/connector_framework_data.xml",
        "data/connector_inbound_endpoint_data.xml",
        "data/seed_real_data_v1.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
