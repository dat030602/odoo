# dn_web_side_view_holidays/__manifest__.py
{
    'name': "LSF Inherit - hr_holidays",
    'summary': "Inherit hr_holidays views with advanced side view support",
    'description': """
    Adds advanced viewing modes to the default Odoo 19 List View for holidays views.
    - Default Mode (Base Odoo behavior).
    - Split View Mode (Splits screen: List on the left, Form on the right).
    - Popup Mode (Opens the Form view in a modal/target new).
    """,
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',
    'category': 'Hidden',
    'version': '19.0.1.0.1',
    'license': 'LGPL-3',
    'depends': ['dn_web_side_view', 'hr_holidays'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'dn_web_side_view_holidays/static/src/*.xml',
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
