{
    'name': 'Meta Migrator - Move Model/Field between Odoo links',
    'version': '19.0.2.0.0',
    'category': 'Technical',
    'summary': 'Step-by-step batch migration of models, fields, views, and server actions with git-style diff and dry-run testing',
    'description': """
Meta Migrator (Odoo 19)
=======================
Step-by-step batch migration of models, fields, views, menus, access rights, record rules, and server actions across Odoo instances via XML-RPC.

Key Highlights:
---------------
* **Top-Down Sequential Execution**: Steps execute strictly in configured sequence order (models, fields, views, server actions, menus, security).
* **Zero-Write Dry-Run Testing (`action_test`)**: Simulates the migration using a virtual in-memory cache, verifying dependencies without modifying target databases.
* **8 Specialized OWL 2 Diff Widgets**: Contextual field viewers (`meta_model_create`, `meta_model_update`, `meta_field_create`, `meta_field_update`, `meta_view_create`, `meta_view_update`, `meta_server_action`, `meta_generic_record`) with attribute diff tables, XML outlines, and risk alerts.
* **Shared CodeDiff Component**: Split & Unified diff views with word-level diffing, fold/unfold, and line navigation.
* **Circular Relational Block Solver**: Contiguous field steps are collapsed into an atomic 3-pass block, resolving complex cross-model dependencies.
* **Non-Destructive View Merging**: Appends new XML elements directly into `<data>` nodes, preserving target modifications.
* **Field Generation Wizard**: One-click batch extraction of manual custom fields from any model into ordered migration steps.
* **Synchronized Verification**: Post-run testing calculates `is_in_sync`, proving 100% parity with zero diff delta.
* **Built-in Documentation**: Standalone user guide available at `/meta_migrator/guide` and linked directly from the migration job form.
""",
    'author': 'Custom',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/guide_templates.xml',
        'views/connection_views.xml',
        'views/migration_views.xml',
        'views/run_views.xml',
        'views/change_views.xml',
        'views/wizard_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'meta_migrator/static/src/js/diff_viewer/diff_algo.js',
            'meta_migrator/static/src/js/diff_viewer/meta_diff.js',
            'meta_migrator/static/src/js/diff_viewer/meta_diff.xml',
            'meta_migrator/static/src/js/diff_viewer/meta_diff.scss',
            'meta_migrator/static/src/js/change_widgets/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
