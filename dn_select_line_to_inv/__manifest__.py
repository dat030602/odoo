# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    "name": "Select SO Lines to Create Invoice",
    # Short summary shown in Apps list
    "summary": "Select specific lines from a Sales Order to create an invoice",
    # Detailed description (optional when using static/description/index.html)
    "description": """
This module allows users to select specific lines from a Sales Order (SO) to create an invoice. It enhances the standard Odoo functionality by providing a more granular control over which items are invoiced, enabling better management of billing processes and customer orders.
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
        "sale",
    ],
    # Data files
    "data": [
        "security/ir.model.access.csv",
        "wizards/sale_make_invoice_views.xml",
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
