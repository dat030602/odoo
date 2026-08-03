{
    'name': "LSF Inherit - website_slides",
    'summary': "Inherit website_slides views with advanced side view support",
    'description': """
        Adds advanced viewing modes to the default Odoo 19 List View for website slides views.
        - Default Mode (Base Odoo behavior).
        - Split View Mode (Splits screen: List on the left, Form on the right).
        - Popup Mode (Opens the Form view in a modal/target new).
    """,
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',
    'category': 'Hidden',
    'version': '19.0.1.0.1',
    'license': 'LGPL-3',
    'depends': ['dn_web_side_view', 'website_slides'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'dn_web_side_view_slides/static/src/*.xml',
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
