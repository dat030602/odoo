{
    'name': 'Form Full Width Toggle',
    'version': '1.0',
    'summary': 'Toggle form full width with a floating button',
    'description': 'Adds a floating button to toggle the form full width and keeps the preference available per user.',
    'category': 'Customizations',
    'author': 'DN',
    'depends': ['base', 'web', 'mail'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'dn_form_full_width/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
