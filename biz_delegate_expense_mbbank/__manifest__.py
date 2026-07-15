# -*- coding: utf-8 -*-

{
    'name': 'Bizapps Delegate Expense MB Bank',
    'version': '16.0.0.1',
    'category': 'Account',
    'description': "Bizapps Delegate Expense MB Bank",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','account'],
    'data': [
        'reports/report_action.xml',
        'reports/delegate_expense_mb_template.xml',
        'reports/delegate_expense_invoice_mb_template.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}