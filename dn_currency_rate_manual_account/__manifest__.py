{
    'name': 'Manual Currency Rate Account',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Selective currency exchange rates on invoices and vendor bills',
    'description': """
Manual Currency Rate Account
============================
This module integrates currency rate selection into invoices and vendor bills (`account.move`).

Key Features:
-------------
* Choose rate mode on invoice: Default or Custom.
* Override `invoice_currency_rate` based on custom rate selection.
* Preserve rate mode and custom exchange rate on credit notes / reversal moves.
* Readonly once invoice is confirmed/posted.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': ['account', 'dn_currency_rate_manual_base'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
