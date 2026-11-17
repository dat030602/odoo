{
    'name': 'Manual Currency Rate Sale Account Bridge',
    'version': '19.0.1.0.0',
    'category': 'Sales/Accounting',
    'summary': 'Transfers currency rate settings from Sales Order to Customer Invoice',
    'description': """
Manual Currency Rate Sale Account Bridge
========================================
Glue module connecting `dn_currency_rate_manual_sale` and `dn_currency_rate_manual_account`.

Key Features:
-------------
* Automatically passes `rate_mode` and `selected_rate_id` from Sales Order to Customer Invoice upon invoice preparation.
* Ensures exact currency conversion consistency from quotation to billing.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': [
        'dn_currency_rate_manual_sale',
        'dn_currency_rate_manual_account',
    ],
    'data': [],
    'auto_install': True,
    'installable': True,
    'application': False,
}
