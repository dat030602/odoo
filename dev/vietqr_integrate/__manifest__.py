{
    'name': 'VietQR Integrate',
    'version': '1.0',
    'category': 'Sale',
    'summary': 'VietQR Integration module',
    'description': """
        VietQR Integration module
        - Manage VietQR bank information
        - Generate QR codes for payments
        - Integrate with Odoo
    """,
    'author': 'Dat Nguyen',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/vietqr_bank.xml',
        'views/vietqr_bank_config.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

