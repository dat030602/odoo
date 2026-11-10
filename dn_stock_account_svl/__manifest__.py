# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock Valuation Layer Core & Costing Engine",
    'version': "19.0.1.0.0",
    'category': "Inventory/Inventory",
    'summary': "Stock Valuation Layer recreation, Standard/AVCO/FIFO costing engine, and completed move modification.",
    'author': "Dyan",
    'license': "LGPL-3",
    'depends': [
        'stock_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/account_move_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_location_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_valuation_layer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
