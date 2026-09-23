{
    'name': 'Meta Migrator - Move Model/Field between Odoo links',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Migrate models, fields, views, and server actions between Odoo systems via XML-RPC',
    'description': """
Meta Migrator
=============
Technical tool for copying:

* Custom models and fields (state = 'manual')
* List, form, and search views from the source system
* Server actions (ir.actions.server) by XML ID

from a source Odoo system to a target Odoo system through XML-RPC.

Connection details (URL, database, username, and password) are stored in reusable
meta.migration.connection records.

Field migration uses two passes to avoid dependency errors:

1. Pass 1: create or update core field properties (ttype, relation, required, and so on).
2. Pass 2: update compute, depends, and related after all model fields exist.
""",
    'author': 'Custom',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/connection_views.xml',
        'views/migration_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
