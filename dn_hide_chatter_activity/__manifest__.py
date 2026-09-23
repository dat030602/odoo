{
    'name': 'Hide Chatter and Activity',
    'version': '1.0',
    'summary': 'Dynamically hide chatter and activity by model',
    'description': 'Provides a setting to hide the chatter or activity views for specific models.',
    'category': 'Customizations',
    'author': 'DN',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/hide_rule_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dn_hide_chatter_activity/static/src/css/hide_chatter.scss',
            'dn_hide_chatter_activity/static/src/js/form_controller_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
