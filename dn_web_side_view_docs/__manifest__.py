{
    'name': "LSF Inherit - documents",
    'summary': "Inherit documents views with advanced side view support",
    'description': """
        Adds advanced viewing modes to the default Odoo 19 List View for documents views.
        - Default Mode (Base Odoo behavior).
        - Split View Mode (Splits screen: List on the left, Form on the right).
        - Popup Mode (Opens the Form view in a modal/target new).
    """,
    'version': '19.0.1.0.1',
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',
    'category': 'Hidden',
    'license': 'LGPL-3',
    'depends': ['dn_web_side_view', 'documents'],
    'data': [],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'dn_web_side_view_docs/static/src/*.xml',
        ],
    },
    # App screenshots / icons
    'images': [
        'static/description/icon.png',
    ],
    'price': 0.00,
    'currency': 'EUR',
}
