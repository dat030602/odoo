{
    'name': "Web Side View",
    'summary': "Add Split View and Popup actions to list view",
    'description': """
        Adds advanced viewing modes to the default Odoo 19 List View:
        - Default Mode (Base Odoo behavior).
        - Split View Mode (Splits screen: List on the left, Form on the right).
        - Popup Mode (Opens the Form view in a modal/target new).
    """,
    'author': 'Dat Nguyen',
    
    'category': 'Hidden',
    'version': '19.0.1.0.0',
    'license': 'OPL-1',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'web_side_view/static/src/*.xml',
            'web_side_view/static/src/*.scss',
            'web_side_view/static/src/*.js',
        ],
    },
    'installable': True,
    'application': False,
}
