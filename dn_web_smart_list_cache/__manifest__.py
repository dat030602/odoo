# -*- coding: utf-8 -*-
{
    'name': 'Smart List Cache - Zero Query Back Navigation',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Eliminate redundant search_read queries when returning from Form to List View with smart DOM patching',
    'description': """
Smart List Cache (Zero-Query Back Navigation)
==============================================
Eliminates redundant search_read queries when users navigate back from Form View to List View in Odoo 18 & 19 (OWL Framework).

Key Features:
- Zero-Query Back Navigation: Prevents duplicate search_read/web_search_read queries on List View restore.
- Smart State & DOM Patching: Locally updates modified rows, removes deleted records, and reflects newly created records.
- Preserves Scroll & UI State: Retains exact UI list state without full reload latency.
- Multi-Model Isolation: Global cache service maintains isolated caches per model.
- High Performance: Saves database load and network traffic for high-frequency navigation workflows.
    """,
    'author': 'Dat Nguyen',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'dn_web_smart_list_cache/static/src/js/smart_list_cache_service.js',
            'dn_web_smart_list_cache/static/src/js/form_controller_patch.js',
            'dn_web_smart_list_cache/static/src/js/relational_model_patch.js',
            'dn_web_smart_list_cache/static/src/js/list_controller_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
