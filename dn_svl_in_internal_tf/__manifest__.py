# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock Valuation Layer & Journal Entries for Internal Transfers",
    'version': "19.0.1.0.0",
    'category': "Inventory/Inventory",
    'summary': "Stock Valuation Layer & Journal Entries for Internal Transfers",
    'author': "Dyan",
    'license': "LGPL-3",
    'depends': [
        'dn_stock_account_svl',
        'stock_account',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/stock_valuation_move_type_data.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
