# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Momo',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 2,
    'summary': "An Irish-American payment provider covering the US and many others.",
    'depends': ['payment','sale_management'],
    'data': [
        # "security/security.xml",
        # "security/ir.model.access.csv",

        'views/payment_provider_views.xml',
        'views/payment_momo_templates.xml',
        # 'views/payment_transaction_views.xml',

        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
    ],
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_momo/static/src/js/payment_form.js',
        ],
        'web.assets_backend': [
        ],
    },
    'license': 'LGPL-3',
}
