# -*- coding: utf-8 -*-

{
    'name': 'Bizapps Account Payment Slip CCV',
    'version': '16.0.0.1',
    'category': 'Account',
    'description': "Bizapps Account Payment Slip",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['account','biz_accounting_voucher_ccv'],
    'data': [
        'reports/report_action.xml',
        'reports/account_payment_slip_template.xml',
        'reports/account_payment_slip_invoice_template.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}