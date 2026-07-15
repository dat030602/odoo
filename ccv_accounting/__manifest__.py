# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "CCV: Kế toán",
    "version": "1.3",
    "category": "",
    "description": """Kế toán""",
    "depends": [
        "sale_stock",
        "sale_management",
        "account_accountant",
        "biz_custom_payment",
        "auto_reconcile_invoice",
        'biz_custom_invoice',
        'biz_manual_currency_exchange_rate',
        'stock',
    ],
    "data": [
        'data/automated_action.xml',
        'security/ir.model.access.csv',
        'wizards/sale_order_to_invoice_views.xml',
        'wizards/wz_account_move_import_tax.xml',
        'views/stock_picking.xml',
        'views/sale_order.xml',
        'views/account_move.xml',
        'views/res_partner.xml',
        'views/res_partner_group.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
