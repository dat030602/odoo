# -*- coding: utf-8 -*-

{
    'name': 'Bizapps Delegate Expense Vietinbank',
    'version': '16.0.0.1',
    'category': 'Account',
    'description': "Bizapps Delegate Expense Vietinbank",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','account','biz_vn_address'],
    'data': [
        'reports/report_action.xml',
        'reports/delegate_expense_vietin_template.xml',
        'reports/delegate_expense_invoice_vietin_template.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}