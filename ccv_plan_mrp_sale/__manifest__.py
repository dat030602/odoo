# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "CCV: Kế hoạch sản xuất/Kế hoạch xuất hàng",
    "version": "1.3",
    "category": "",
    "description": """Kế hoạch sản xuất/Kế hoạch xuất hàng""",
    "depends": [
        "sale_stock",
        "sale_management",
        "mrp",
        'ccv_accounting',
        'report_xlsx',
    ],
    "data": [
        'data/parameter.xml',
        'security/ir.model.access.csv',
        'views/ccv_sale_plan_export_line.xml',
        'views/ccv_sale_plan_export_line2.xml',
        'views/ccv_sale_plan_export.xml',
        'views/ccv_mrp_plan_export.xml',
        'views/ccv_secondary_label.xml',
        'views/stock_picking_type.xml',
        'views/factory_product_default.xml',
        'views/mrp_production.xml',
        'views/action.xml',
        'reports/bao_cao_ccv_report.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
