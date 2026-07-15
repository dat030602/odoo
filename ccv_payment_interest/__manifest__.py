# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "CCV: Lãi suất thanh toán",
    "version": "1.3",
    "category": "",
    "description": """Lãi suất thanh toán""",
    "depends": [
        "account_accountant",
        "sale_management",
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/partner_debt_cron.xml',
        'data/debt_interest_config_parameters.xml',
        'views/interest_rate_year_views.xml',
        'views/partner_debt_interest_line.xml',
        'views/partner_debt_interest.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
