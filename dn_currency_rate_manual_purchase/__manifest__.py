{
    'name': 'Manual Currency Rate Purchase',
    'version': '19.0.1.0.0',
    'category': 'Purchases/Purchases',
    'summary': 'Selective currency exchange rates on purchase orders',
    'description': """
Manual Currency Rate Purchase
=============================
This module integrates currency rate selection into Purchase Orders (`purchase.order`).

Key Features:
-------------
* Choose rate mode on purchase order: Default or Custom.
* Override `currency_rate` based on custom rate configuration.
* Readonly once purchase order is confirmed (`state not in ('draft', 'sent')`).
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': ['purchase', 'dn_currency_rate_manual_base'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
