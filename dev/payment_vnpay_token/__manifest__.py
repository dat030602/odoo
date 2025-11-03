# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: VNPay Token',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 2,
    'summary': "VNPay Token payment provider for tokenized payments",
    'description': """
        VNPay Token Payment Provider
        ===========================
        
        This module provides tokenized payment functionality for VNPay.
        It allows customers to save their payment methods and reuse them for future transactions.
        
        Features:
        - Token creation and management
        - Token-based payments
        - Token deletion
        - Secure token storage
    """,
    'depends': ['payment', 'payment_vnpay'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'views/payment_token_views.xml',
        'views/payment_vnpay_token_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_vnpay_token/static/src/js/payment_form.js',
            'payment_vnpay_token/static/src/js/payment_form_i18n.js',
            'payment_vnpay_token/static/src/css/payment_form.css',
        ],
        'web.assets_backend': [
        ],
    },
    'license': 'LGPL-3',
}
