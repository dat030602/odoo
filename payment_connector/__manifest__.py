# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Connector',
    'version': '1.0',
    'category': 'Accounting',
    'sequence': 2,
    'summary': "An Irish-American payment provider covering the US and many others.",
    'depends': ['payment','sale_management'],
    'data': [
        # "security/security.xml",
        "security/ir.model.access.csv",

        'views/menu.xml',
        'views/payment_model_api_view.xml',
        'views/payment_model_line_view.xml',
        'views/payment_model_view.xml',
        'views/payment_response_view.xml',
    ],
    'application': False,
    'assets': {
        'web.assets_frontend': [
            # 'payment_momo/static/src/js/payment_form.js',
        ],
        'web.assets_backend': [
        ],
    },
    'license': 'LGPL-3',
}
