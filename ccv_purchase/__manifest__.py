# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "CCV: Mua hàng",
    "version": "1.3",
    "category": "",
    "description": """Mua hàng""",
    "depends": [
        "purchase_stock","purchase_customs_infomation_ccv","trp_approve","ccv_bao_cao", "biz_manual_currency_exchange_rate", "biz_import_inv_value_by_xlsx"
    ],
    "data": [
        'data/ir_config_parameter.xml',
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
        'views/purchase_sign_requests.xml',
        'wizards/stock_move_wizard.xml',
        'wizards/edit_account_move_exchange.xml',
        'views/res_currency.xml',
        'views/product_template.xml',
        'views/res_config_settings.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
