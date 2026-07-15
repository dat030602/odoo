# -*- coding: utf-8 -*-
{
    "name": "PCV: Check Exchange Rate",
    "version": "1.0",
    "category": "",
    "description": "PCV: Check Exchange Rate",
    "depends": [
        "biz_manual_currency_exchange_rate",
    ],
    "data": [
        'data/account_move_tag_data.xml',
        'security/ir.model.access.csv',
        'wizards/check_exchange_rate_wizard_views.xml',
        'wizards/confirm_post_threshold_entries_wizard_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
