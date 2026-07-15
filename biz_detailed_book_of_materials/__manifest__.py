# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bizapps - Sổ chi tiết vật liệu dụng cụ (S10-DN)',
    'version': '16.0.0.1',
    'summary': 'Sổ chi tiết vật liệu dụng cụ (S10-DN)',
    'description': """Sổ chi tiết vật liệu dụng cụ (S10-DN)""",
    'category': 'Accounting',
    'website': "http://www.bizapps.vn",
    'author': 'support@bizapps.vn',
    'depends': [
        'base','account','biz_stock_summary_report','mrp','biz_to_stock_backdate','ccv_accounting','trp_approve'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/parameter.xml',

        'reports/report_action.xml',
        'reports/material_detail_book_pdf.xml',
        'views/material_detail_book_view.xml',
        'views/material_detail_book_line.xml',
        'views/account_view.xml',
        'views/mrp_production.xml',
    ],
    "license": "OPL-1",
    'installable': True,
    'application': False,
    'auto_install': False,
}
