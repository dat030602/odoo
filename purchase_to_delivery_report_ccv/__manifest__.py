# -*- coding: utf-8 -*-
{
    "name": "Purchase to Delivery Report",
    "summary": "Export Excel report of delivery orders created from purchase orders (by container number)",
    "version": "16.0.1.0.0",
    "category": "Inventory/Reporting",
    "author": "Your Company",
    "website": "",
    "depends": ["purchase_to_delivery_ccv", "biz_to_stock_backdate", "biz_conveyor_picking", "report_xlsx"],
    "data": [
        "data/server_actions.xml",
        "data/parameter.xml",
        "wizard/export_delivery_report_wizard_views.xml",
        "views/purchase_order_views.xml",
        "views/export_delivery_report_ccv_views.xml",
        "views/stock_picking_views.xml",
        "report/report.xml",
        "report/export_delivery_report_ccv_pdf_template.xml",
        "security/ir.model.access.csv"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "maintainers": ["leonix"],
}
