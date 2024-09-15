# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Momo',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence':-1,
    'summary': 'Integrate your POS with a Momo payment terminal',
    'description': '',
    'data': [
    ],
    'depends': ['point_of_sale', 'payment_momo'],
    'installable': True,
    'data' :[
        'views/account_payment_views.xml'
    ],
    'assets': {
        'point_of_sale.assets_prod': [
            'pos_momo/static/src/app/**/*',
        ],
    },
    'license': 'LGPL-3',
}
