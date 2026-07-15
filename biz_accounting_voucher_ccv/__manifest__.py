# -*- coding: utf-8 -*-

{
    'name': 'Bizapps Accounting Voucher CCV',
    'version': '16.0.0.1',
    'category': 'Account',
    'description': "Bizapps Account Payment",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['account'],
    'data': [
        'data/ir_sequence.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}