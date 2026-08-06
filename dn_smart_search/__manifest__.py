# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    'name': 'Smart Search',

    # Short summary shown in Apps list
    'summary': 'Global cross-model search from a single search box',

    # Detailed description (optional when using static/description/index.html)
    'description': """
Smart Search provides a fast, centralized search experience across multiple
Odoo models from a single search box.

Instead of navigating through different menus, users can search records from
multiple business objects in one place and open the desired record instantly.

Features:
- Global search across multiple models
- Fast and responsive search interface
- Configurable searchable models
- Keyboard-friendly navigation
- Lightweight OWL implementation
- Easy integration with existing Odoo modules
- Designed for Odoo 19
    """,

    # Author information
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',

    # Module category
    'category': 'Tools',

    # Version format: OdooVersion.ModuleVersion
    'version': '19.0.1.0.0',

    # License (required for paid apps)
    'license': 'OPL-1',

    # Dependencies
    'depends': [
        'web',
    ],

    # Data files
    'data': [
        'security/ir.model.access.csv',
        'views/smart_search_views.xml',
    ],

    # App icon
    'images': [
        'static/description/icon.png',
    ],

    # Static assets
    'assets': {
        'web.assets_backend': [
            'dn_smart_search/static/src/**/*',
        ],
    },

    # Demo data
    'demo': [],

    # Hooks
    'post_init_hook': 'post_init_hook',

    # Installation
    'installable': True,
    'application': False,
    'auto_install': False,

    # Pricing
    'price': 10.00,
    'currency': 'EUR',
}