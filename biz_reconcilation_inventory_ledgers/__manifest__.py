# -*- coding: utf-8 -*-

{
    'name': 'Bizapps Reports Reconciliation Inventory and Ledgers',
    'version': '16.0.0.1',
    'category': 'Account',
    'description': "Bizapps Reports Reconciliation Inventory and Ledgers",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['account', 'report_xlsx',],
    'data': [
        'security/ir.model.access.csv',
        'report/action_report.xml',
        'wizard/wz_reconcilation_inventory_ledgers_view.xml',
        'views/account_account_view.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}