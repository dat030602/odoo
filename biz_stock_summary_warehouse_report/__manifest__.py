# -*- coding: utf-8 -*-
{
    'name': "Bizapps - Stock summary warehouse report",
    'description': """
        Stock summary report
    """,
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    'company': 'Bizapps',
    'support': 'support@bizapps.vn',
    'category': 'Inventory',
    'summary': """""",
    'version': '16.0.0.1',
    'depends': [
        'biz_stock_summary_report', 'biz_import_inv_value_by_xlsx'
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/rp_summary_ie_inv_pdf.xml',
        'views/summary_ie_inventory_view.xml',
        'views/summary_ie_inventory_line_view.xml',
    ],
    "license": "OPL-1",
    "installable": True,
    'auto_install': False,
}
