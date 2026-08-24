{
    'name': 'Meta Blueprint Schema',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Meta-builder: define models, fields, actions, views, and access rights via a unified blueprint with drag-and-drop ordering.',
    'description': """
Meta Blueprint Schema
=====================
A meta-builder framework that allows users to define Odoo models, fields,
server actions, views, and access rights through a single blueprint interface.

Key features:
- Unified schema table combining Models and Fields with drag-and-drop sequence ordering.
- Execute Build button processes items in exact list order (Models first, then Fields, then Actions, Views, Access).
- Full support for computed fields, related fields, monetary fields, one2many, many2many, etc.
- XML ID registration for actions and views.
""",
    'author': 'MJB Solutions',
    'website': 'https://www.mjbsolutions.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/meta_blueprint_views.xml',
        'views/meta_blueprint_action_views.xml',
        'views/meta_blueprint_view_views.xml',
        'views/meta_blueprint_access_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
