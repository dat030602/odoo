{
    'name': "LSF Inherit - timesheet_grid",
    'summary': "Inherit timesheet_grid views with advanced side view support",
    'description': """
        Adds advanced viewing modes to the default Odoo 19 List View for timesheet grid views.
        - Default Mode (Base Odoo behavior).
        - Split View Mode (Splits screen: List on the left, Form on the right).
        - Popup Mode (Opens the Form view in a modal/target new).
    """,
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',
    'category': 'Hidden',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['dn_web_side_view', 'timesheet_grid'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'dn_web_side_view_timesheet/static/src/*.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 0.00,
    'currency': 'EUR',
}
