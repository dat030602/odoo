# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Dynamic Excel Report Framework",
    "summary": "Low-code Excel report generation framework for Odoo",
    "version": "19.0.1.0.0",
    "category": "Reporting",
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "license": "AGPL-3",
    "depends": [
        "base",
        "web",
        "report_xlsx",
    ],
    "external_dependencies": {
        "python": ["xlsxwriter"],
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/excel_report_views.xml",
        "views/excel_template_views.xml",
        "views/excel_format_views.xml",
        "views/excel_column_views.xml",
        "views/excel_layout_views.xml",
        "views/excel_menu_views.xml",
        "demo/demo_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dn_dynamic_excel_report/static/src/js/excel_report_widget.js",
        ],
    },
    "demo": [
        "demo/demo_report.xml",
    ],
    "installable": True,
    "application": True,
    "development_status": "Beta",
}