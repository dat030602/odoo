# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Báo cáo tồn kho',
    'version': '1.3',
    'category': 'Inventory/Inventory Report',
    'description': """Báo cáo tồn kho""",
    'depends': [
        'stock','ccv_bao_cao',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/bien_ban_kiem_ke_vat_tu_hang_hoa.xml',
        'report/bao_cao_ccv_report.xml',
        'views/stock_quant.xml',
        'views/report_line2_views.xml',
        'views/report_line_views.xml',
        'views/report_views.xml',
        'views/menu.xml',
    ],
    'assets': {
    },
    'installable': True,
    'license': 'LGPL-3',
}
