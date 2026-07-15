# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Sổ tổng hợp bán hàng',
    'version': '1.0',
    'category': 'Inventory/Inventory Report',
    'description': """Sổ tổng hợp bán hàng""",
    'depends': [
        'sale_management','ccv_custom_field', 'biz_custom_invoice'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ccv_report_debt_sale_line_views.xml',
        'views/ccv_report_debt_sale_total_line_views.xml',
        'views/ccv_report_debt_sale_views.xml',
        'report/bao_cao_ccv_report.xml',
    ],
    'assets': {
    },
    'installable': True,
    'license': 'LGPL-3',
}
