# -*- coding: utf-8 -*-

{
    'name': 'Bizapps Internal Transfer Accounting Voucher CCV',
    'version': '16.0.0.1',
    'category': 'Account',
    'description': "Bizapps Account Payment Slip",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['account','biz_accounting_voucher_ccv', 'biz_accounting_other_business'],
    'data': [
        'reports/report_action.xml',
        'reports/report_internal_transfer_template.xml',
        'reports/report_internal_transfer_invoice_template.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}