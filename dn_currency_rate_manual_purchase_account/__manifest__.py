{
    'name': 'Manual Currency Rate Purchase Account Bridge',
    'version': '19.0.1.0.0',
    'category': 'Purchases/Accounting',
    'summary': 'Transfers currency rate settings from Purchase Order to Vendor Bill',
    'description': """
Manual Currency Rate Purchase Account Bridge
============================================
Glue module connecting `dn_currency_rate_manual_purchase` and `dn_currency_rate_manual_account`.

Key Features:
-------------
* Automatically passes `rate_mode` and `selected_rate_id` from Purchase Order to Vendor Bill upon bill creation.
* Ensures exact currency conversion consistency from RFQ/PO to vendor bill.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': [
        'dn_currency_rate_manual_purchase',
        'dn_currency_rate_manual_account',
    ],
    'data': [],
    'auto_install': True,
    'installable': True,
    'application': False,
}
