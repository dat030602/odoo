{
    'name': 'Manual Currency Rate Base',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Currencies',
    'summary': 'Core mixin and security group for manual and selective currency exchange rates',
    'description': """
Manual Currency Rate Base
=========================
This module provides the core mixin and security groups enabling currency rate
selection across business documents (Invoices, Sales Orders, Purchase Orders).

Key Features:
-------------
* Introduces `currency.rate.mixin` with rate_mode:
  - default: standard Odoo rate lookup.
  - custom: pick a historical rate from res.currency.rate.
* Security group `group_manual_currency_rate` to restrict manual rate editing.
* Helper method `_get_dynamic_rate` to calculate direct/indirect rates.
* Enhanced `display_name` formatting for rate selection dropdowns.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/currency_rate_manual_security.xml',
        'views/res_currency_rate_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
