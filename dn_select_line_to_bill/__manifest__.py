# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    "name": "Select PO Lines to Create Bill",
    # Short summary shown in Apps list
    "summary": "Select specific lines from a Purchase Order to create a bill",
    # Detailed description (optional when using static/description/index.html)
    "description": """
This module allows users to select specific lines from a Purchase Order (PO) to create a bill. It enhances the standard Odoo functionality by providing a more granular control over which items are billed, enabling better management of billing processes and customer orders.
    """,
    # Author information
    "author": "Dat Nguyen",
    # Module category
    "category": "Tools",
    # Version format: OdooVersion.ModuleVersion
    "version": "19.0.1.0.1",
    # License
    "license": "LGPL-3",
    # Dependencies
    "depends": [
        "purchase",
    ],
    # Data files
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order.xml",
        "wizards/purchase_make_invoice_views.xml",
    ],
    # Static assets
    "assets": {},
    # Demo data
    "demo": [],
    # Installation
    "installable": True,
    "application": False,
    "auto_install": False,
}
