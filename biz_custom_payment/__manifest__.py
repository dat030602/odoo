# -*- coding: utf-8 -*-
{
    'name': 'Bizapps - Custom Payment',
    'version': '16.0.0.1',
    'category': 'Stock',
    'description': "Payment menu income and expenditure utilities when creating new and cloning",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','payment','account','biz_accounting_voucher_ccv','ccv_sql','account_reports','account_accountant'],
    'data': [
        'views/account_payment.xml',
        'views/account_move.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'biz_custom_payment/static/src/xml/account_reconciliation.xml',
        ]
    },
    'installable': True,
    'application': False,
    "license": "OPL-1",
}