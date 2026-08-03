{
    'name': "LSF Inherit - account_accountant",
    'summary': "Inherit account_accountant views with advanced side view support",
    'description': """
        Adds advanced viewing modes to the default Odoo 19 List View for accountant views.
        - Default Mode (Base Odoo behavior).
        - Split View Mode (Splits screen: List on the left, Form on the right).
        - Popup Mode (Opens the Form view in a modal/target new).
    """,
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',
    'category': 'Hidden',
    'version': '19.0.1.0.1',
    'license': 'LGPL-3',
    'depends': ['dn_web_side_view', 'account_accountant'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'dn_web_side_view_accountant/static/src/*.xml',
        ],
    },
    # App screenshots / icons
    'images': [
        'static/description/icon.png',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 0.00,
    'currency': 'EUR',
}
