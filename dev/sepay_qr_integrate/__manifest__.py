{
    'name': 'Sepay QR Integrate',
    'version': '1.0',
    'category': 'Sale',
    'summary': 'Sepay QR Integration module',
    'description': """
        Sepay QR Integration module
        - Manage Sepay QR bank information
        - Generate QR codes for payments using Sepay API
        - Integrate with Odoo
    """,
    'author': 'Dat Nguyen',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/sepay_bank.xml',
        'views/sepay_bank_config.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

