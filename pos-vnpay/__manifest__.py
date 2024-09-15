# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS VNPay',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence':-1,
    'summary': 'Integrate your POS with a VNPay payment terminal',
    'description': '',
    'data': [
        'security/ir.model.access.csv',

        'views/pos_payment_method_views.xml',
        'views/assets_vnpay.xml',

    ],
    'depends': ['point_of_sale', 'payment_vnpay'],
    'installable': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_vnpay/static/src/js/*.js',
            'pos_vnpay/static/src/xml/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
