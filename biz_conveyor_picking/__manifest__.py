# -*- coding: utf-8 -*-

{
    'name': 'Bizapps - Conveyor',
    'version': '16.0.0.1',
    'category': 'Stock',
    'description': "Connect conveyor (maydemdemo)",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','stock','product','sale_stock'],
    'data': [
        'data/ir_cron.xml',

        'security/ir.model.access.csv',
        'views/res_config_view.xml',
        'views/product_view.xml',
        'views/stock_picking_view.xml',
        'views/conveyor_log_view.xml',
        'views/conveyor_data_view.xml',
        'views/conveyor_product_data_view.xml',
        'views/uom_uom_view.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}