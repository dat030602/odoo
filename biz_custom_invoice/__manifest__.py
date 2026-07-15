# -*- coding: utf-8 -*-
{
    'name': 'Bizapps - Custom Invoice',
    'version': '16.0.0.1',
    'category': 'Invoice',
    'description': "Adjust and improve the collection and payment process and add features to make it easier to input",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','account','biz_sales_invoice_list_ccv'],
    'data': [
        'views/account_account.xml',
        'views/account_move.xml'
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}