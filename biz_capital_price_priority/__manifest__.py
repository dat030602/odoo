# -*- coding: utf-8 -*-
{
    # Required
    "name": "Biz Capital Price Priority",

    # Information
    "category": "Accounting",
    "version": "1.0",
    "application": False,
    "auto_install": False,
    "installable": True,
    "summary": "Module for managing capital price with account selection wizard.",
    "description": "This module provides functionality to manage capital price and includes a wizard for selecting debit and credit accounts.",
    "author": "Your Company",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://yourcompany.com",
    "sequence": 100,
    "license": "OPL-1",

    # Available packages
    "depends": [
        "biz_capital_price",
    ],
    "data": [
        'views/mrp_production_view.xml',
    ]
}
