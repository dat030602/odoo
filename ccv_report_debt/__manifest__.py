# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Đối chiếu doanh thu',
    'version': '1.3',
    'category': 'Inventory/Inventory Report',
    'description': """Báo cáo tồn kho""",
    'depends': [
        'sale_management','ccv_bao_cao',
    ],
    'data': [
        'report/rp_customer_receivables.xml',
        'report/bao_cao_ccv_report.xml',
        'views/alpha_report.xml',
    ],
    'assets': {
    },
    'installable': True,
    'license': 'LGPL-3',
}
