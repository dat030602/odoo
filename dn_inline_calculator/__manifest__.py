# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    'name': 'Inline Calculator',

    # Short summary shown in Apps list
    'summary': 'Type mathematical expressions directly into numeric fields',

    # Detailed description (optional when using static/description/index.html)
    'description': """
Inline Calculator for Odoo 19 allows users to enter mathematical expressions
directly into Float, Integer, and Monetary fields.

Instead of using an external calculator, users can type formulas such as
"15 * 1.1", "(100 + 50) / 2", or "250 - 15" directly into numeric fields.
The expression is automatically evaluated when the field loses focus.

Features:
- Supports Float, Integer and Monetary fields
- Automatic expression evaluation
- Supports +, -, *, / operators
- Supports parentheses
- Safe validation before evaluation
- Falls back to the standard Odoo parser for invalid expressions
- Lightweight OWL component patch
- No server-side modifications required
    """,

    # Author information
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',

    # Module category
    'category': 'Tools',

    # Version format: OdooVersion.ModuleVersion
    'version': '19.0.1.0.1',

    # License for free module
    'license': 'LGPL-3',

    # Dependencies
    'depends': [
        'base',
        'web',
    ],

    # Data files
    'data': [
    ],

    # App image
    'images': [
        'static/description/icon.png',
    ],

    # Static assets
    'assets': {
        'web.assets_backend': [
            'dn_inline_calculator/static/src/js/inline_calculator.js',
        ],
    },

    # Demo data
    'demo': [],

    # Installation
    'installable': True,
    'application': False,
    'auto_install': False,
}