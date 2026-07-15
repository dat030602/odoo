# -*- coding: utf-8 -*-

{
    "name": "Bizapps Payment Request",
    "summary": "Payment Request",
    "version" : "16.0.0.1",
    "category": "Payment Request",
    "website": "https://bizapps.vn/ung-dung",
    "author": "support@bizapps.vn",
    "depends": [
        'trp_approve', 'ccv_report',
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/ir_rule_views.xml',
        'data/payment_request_data.xml',
        'views/payment_product_note_views.xml',
        'views/account_payment_view.xml',
        'views/alpha_internal_account_views.xml',
        'views/hr_expense_views.xml',
        'views/payment_request_view.xml',
        'views/payment_request_unc_view.xml',
        'views/trp_approve_config.xml',
        'views/res_partner_bank_views.xml',
    ],
    "application": False,
    "installable": True,
    "sequence": 1,
    'license': 'OPL-1'

}