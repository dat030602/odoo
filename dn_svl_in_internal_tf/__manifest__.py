# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stock Valuation Layer - Internal Transfer',
    'version': '19.0.1.0.0',
    'summary': 'Generate SVL & accounting journal entries for internal transfers between warehouses with different valuation accounts',
    'description': """
Description
===========
This module extends Odoo 19 stock valuation to automatically generate:

* A **pair of Stock Valuation Layer (SVL)** records whenever a stock.move
  is completed between two internal locations under real-time (perpetual)
  valuation.
* A **Journal Entry (account.move)** to record the account difference
  between the source and destination warehouse
  (only created when the two accounts differ).

Account resolution priority:
1. Account set directly on the ``stock.location``.
2. Recursive lookup up the location parent hierarchy.
3. Fallback to ``product.category.property_stock_valuation_account_id``.
    """,
    'author': 'DN Dev',
    'category': 'Inventory/Inventory',
    'depends': ['stock_account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/stock_location_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
