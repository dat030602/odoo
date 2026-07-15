# -*- coding: utf-8 -*-
{
    # Required
    "name": "Biz Capital Price",

    # Information
    "category": "Accounting",
    "version": "1.0",
    "application": False,
    "auto_install": False,
    "installable": True,
    "summary": "Module for managing capital price with account selection wizard.",
    "description": "This module provides functionality to manage capital price and includes a wizard for selecting debit and credit accounts.",
    "author": "Your Company",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://yourcompany.com",
    "sequence": 100,
    "license": "OPL-1",

    # Available packages
    "depends": [
        "account",'stock_landed_costs', 'biz_stock_summary_report', 'report_xlsx', 'ccv_sql',
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_selection_wizard_view.xml",
        "views/average_capital_price_end_period_views.xml",
        'views/stock_valuation_layer.xml',
        'views/average_price_end_period_mass.xml',
        'views/stock_move_line_view.xml',
        'views/stock_warehouse_view.xml',
        'views/costs_allocated_directly_customer_view.xml',
        'views/account_move_views.xml',
        'views/uom_view.xml',
        'views/res_config_settings.xml',

        'reports/rp_average_period_pdf.xml',
        'reports/costing_rp_pdf_template.xml',
        'reports/report_action.xml'
    ]
}
