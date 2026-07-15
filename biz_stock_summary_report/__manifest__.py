# -*- coding: utf-8 -*-
{
    'name': "Bizapps - Stock summary report",
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
        'base', 'report_xlsx','biz_ccv_mrp',
        'stock','stock_account','stock_landed_costs','biz_details_sales_book_by_customer'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'reports/rp_summary_ie_inv_pdf.xml',
        'reports/report_action.xml',
        'views/summary_ie_inventory_line_view.xml',
        'views/summary_ie_inventory_view.xml',
    ],
    "license": "OPL-1",
    "installable": True,
    'auto_install': False,
}
