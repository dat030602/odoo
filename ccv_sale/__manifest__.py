# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "CCV Sale",
    "version": "1.3",
    "category": "",
    "description": """CCV Sale""",
    "depends": [
        "sale_management",
        "biz_viettel_sinvoice_v2",
        "sign",
        "trp_approve",
        "ccv_bao_cao",
    ],
    "data": [
        'data/sever.xml',
        'data/cron.xml',
        'data/rule.xml',
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/sale_bonus_price_unit.xml',
        'views/sale_ccv_promotion.xml',
        'views/sale_order.xml',
        'views/sale_order_line.xml',
        'views/vietqr_bank.xml',
        'views/vietqr_bank_config.xml',
        'views/sale_sign_requests.xml',
        'views/trp_approve_config_line.xml',
        'views/product.xml',
        'views/menu.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
