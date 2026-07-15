# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "CCV Bonus History Report",
    "version": "1.0",
    "category": "Reporting",
    "description": """CCV Bonus History Report Module""",
    "depends": [
        "ccv_sale",
        "report_xlsx",
    ],
    "data": [
        'data/sever.xml',
        'wizard/bonus_history_report_wizard.xml',
        'report/report.xml',
        'views/sale_bonus_price_unit.xml',
        'views/menu.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
