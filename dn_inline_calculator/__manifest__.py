# -*- coding: utf-8 -*-
{
    'name': 'Inline Calculator',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'In-line Calculator for Numeric Fields',
    'description': """
Inline Calculator for Odoo 19
==============================

This module allows users to enter mathematical expressions directly into numeric input fields
and have them automatically calculated and validated without errors.

Features:
* Enter expressions like "15*1.1" directly into quantity or price fields
* Automatic calculation and validation without red border errors
* Supports basic arithmetic operations: +, -, *, /
* Works with decimal numbers and parentheses
* No need to use external calculator tools
* Uses modern OWL framework for seamless integration

Usage:
1. Navigate to any form with numeric fields (quantity, price, etc.)
2. Type a mathematical expression (e.g., "15*1.1" or "100+50*0.1")
3. Press Tab or click outside the field
4. The result will be automatically calculated and validated

This feature is commonly found in professional accounting software and greatly
improves data entry efficiency.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'assets': {
        'web.assets_backend': [
            'dn_inline_calculator/static/src/js/inline_calculator.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
