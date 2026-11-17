{
    'name': 'Manual Currency Rate Sale',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Selective currency exchange rates on sales orders',
    'description': """
Manual Currency Rate Sale
=========================
This module integrates currency rate selection into Sales Orders (`sale.order`).

Key Features:
-------------
* Choose rate mode on sales order: Default or Custom.
* Override `currency_rate` based on custom rate configuration.
* Readonly once sales order is confirmed (`state not in ('draft', 'sent')`).
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': ['sale_stock', 'dn_currency_rate_manual_base'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
