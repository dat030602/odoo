# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    'name': 'Duplicate Customer Detection',

    # Short summary shown in Apps list
    'summary': 'Detect and prevent duplicate customer entries',

    # Detailed description (optional when using static/description/index.html)
    'description': """
This module provides functionality to detect and prevent duplicate customer entries in the system. It helps maintain data integrity by ensuring that each customer is unique based on specified criteria such as email, phone number, or other identifiers. The module can be configured to automatically check for duplicates when creating or updating customer records, and it can provide suggestions for merging duplicate entries.
    """,

    # Author information
    'author': 'Dat Nguyen',

    # Module category
    'category': 'Tools',

    # Version format: OdooVersion.ModuleVersion
    'version': '19.0.1.0.1',

    # License
    'license': 'LGPL-3',

    # Dependencies
    'depends': [
        'sale',
        'purchase',
        'account',
        'crm',
        'contacts',
    ],

    # Data files
    'data': [
        'views/account_move.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml',
        'views/crm_lead.xml',
    ],

    # Static assets
    'assets': {
        'web.assets_backend': [
        ],
    },

    # Demo data
    'demo': [],

    # Installation
    'installable': True,
    'application': False,
    'auto_install': False,
}
