# -*- coding: utf-8 -*-
{
    # Required
    "name": "BizApps - Profit Loss Statement",

    # Information
    "version": "16.0.0.2",
    "category": "Accounting",
    "application": True,
    "auto_install": False,
    "installable": True,
    "summary": "",
    "description": "",
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "sequence": 100,
    "license": "OPL-1",

    # Available packages
    "depends": ["base", "account", "account_accountant", "report_xlsx", "l10n_vn", "biz_vietnamese_accounting_menu"],
    "data": [
        # Security
        "security/ir.model.access.csv",
        "security/security.xml",
        # Data
        "data/business_activities_config_data.xml",
        # Report
        'report/report_business_pdf_template.xml',
        "report/report_view.xml",
        # Views
        "views/account_view.xml",
    ],
}
