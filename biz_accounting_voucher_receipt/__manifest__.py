# -*- coding: utf-8 -*-

{
    'name': 'Bizapps - Accounting voucher receipt',
    'version': '16.0.0.1',
    'category': 'Account',
    'description': "Accounting voucher receipt",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['biz_accounting_voucher_ccv', 'biz_accounting_other_business'],
    'data': [

        'reports/rp_accounting_voucher_receipt.xml',
        'reports/rp_accounting_voucher_receipt_invoice.xml',
        'reports/report_action.xml'
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}