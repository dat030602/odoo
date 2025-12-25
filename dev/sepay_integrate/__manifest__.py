{
    'name': 'SePay Integrate',
    'version': '1.0',
    'category': 'Sale',
    'summary': 'SePay Integrate module',
    'description': """
        SePay Integrate module
        - Integrate with SePay API
        - Support MBBank and other banks via SePay
        - Real-time transaction synchronization
        - Webhook support for payment notifications
        - Integrate with Odoo
    """,
    'author': 'Dat Nguyen',
    'depends': ['sale_management', 'account', 'vietqr_integrate'],
    'data': [
        'security/ir.model.access.csv',
        'views/sepay_config.xml',
        'views/account_payment.xml',
        'wizards/sepay_transaction_wizard.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
