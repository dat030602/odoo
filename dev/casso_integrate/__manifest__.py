{
    'name': 'Casso Integrate',
    'version': '1.0',
    'category': 'Sale',
    'summary': 'Casso Integrate module',
    'description': """
        Casso Integrate module
        - Integrate with Casso
        - Integrate with Odoo
    """,
    'author': 'Dat Nguyen',
    'depends': ['sale_management', 'account', 'vietqr_integrate'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/casso_transaction_wizard.xml',
        'views/vietqr_bank.xml',
        'views/casso_config.xml',
        'views/account_payment.xml',
        'views/casso_webhook.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
