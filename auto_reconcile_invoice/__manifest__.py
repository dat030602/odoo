# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "Automatic Reconciliation",
    "version": "1.3",
    "category": "",
    "description": """Automatic Reconciliation""",
    "depends": [
        "account_accountant",
        "sale_management",
        "purchase",
        "ccv_custom_field",
        "ccv_sale",
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/server_action.xml',
        'data/rule.xml',
        'data/sequence.xml',
        'views/bank_statement_line_views.xml',
        'views/bank_debit_statement_line_views.xml',
        'views/bank_credit_saoke_line_views.xml',
        'views/bank_debit_saoke_line_views.xml',
        'views/account_payment.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml',
        'views/vietqr_bank_transaction_views.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
