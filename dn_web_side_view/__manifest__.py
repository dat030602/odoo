# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    'name': 'Web Side View',

    # Short summary of features (1 sentence, shown in app search list)
    'summary': 'Enhance Odoo list views with split screen and popup form viewing modes',

    # Detailed description (can be omitted if static/description/index.html exists)
    'description': """
Web Side View enhances the standard Odoo 19 List View by adding flexible
record viewing modes without changing the default workflow.

Features:
- Default mode with standard Odoo list behavior
- Split View mode: display list view on the left and form view on the right
- Popup mode: open form views in modal windows or separate targets
- Improved productivity when reviewing and editing multiple records
- Seamless integration with existing Odoo web client
- Lightweight frontend extension using Odoo OWL framework
    """,

    # Author and website (required by App Store)
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',

    # Module category on Odoo Store
    'category': 'Tools',

    # Version format: [Odoo version].[module version]
    'version': '19.0.1.0.0',

    # License (MUST be OPL-1 for paid apps)
    'license': 'OPL-1',


    # Dependencies (modules this module requires)
    'depends': [
        'web',
    ],

    # Data files loaded at install/upgrade
    'data': [],

    # App screenshots / icons
    'images': [
        'static/description/icon.png',
    ],

    # Static assets (JS, CSS, SCSS, QWeb templates)
    'assets': {
        'web.assets_backend': [
            'dn_web_side_view/static/src/*.xml',
            'dn_web_side_view/static/src/*.scss',
            'dn_web_side_view/static/src/*.js',
        ],
    },

    # Demo data (only loaded in demonstration mode)
    'demo': [],

    # Installation configuration
    'installable': True,       # Whether the module can be installed
    'application': False,      # Utility module, not a standalone application
    'auto_install': False,     # Do not auto-install with dependencies

    # Pricing (for paid apps on Odoo Store)
    'price': 15.00,
    'currency': 'EUR',
}
