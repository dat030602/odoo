# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Báo cáo hàng tồn kho khu vực',
    'version': '1.3',
    'category': 'Inventory/Inventory Report',
    'description': """Báo cáo hàng tồn kho khu vực""",
    'depends': [
        'sale_management','ccv_bao_cao','ccv_plan_mrp_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/bao_cao_ccv_report.xml',
        'views/report_stock_order_line_ccv_view.xml',
        'views/report_stock_order_ccv_view.xml',
    ],
    'assets': {
    },
    'installable': True,
    'license': 'LGPL-3',
}
