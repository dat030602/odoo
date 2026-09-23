{
    'name': 'X2Many Fullscreen',
    'version': '1.0',
    'summary': 'Open One2many and Many2many lists in fullscreen mode',
    'description': 'Adds a button to X2Many fields to open them in fullscreen mode.',
    'category': 'Customizations',
    'author': 'DN',
    'depends': ['base', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'dn_x2many_fullscreen/static/src/css/x2many_fullscreen.scss',
            'dn_x2many_fullscreen/static/src/js/x2many_fullscreen.js',
            'dn_x2many_fullscreen/static/src/xml/x2many_fullscreen.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
