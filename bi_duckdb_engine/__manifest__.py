# -*- coding: utf-8 -*-
{
    # Module Metadata
    'name': 'BI DuckDB WASM Engine',
    'version': '19.0.1.0.0',
    'category': 'Reporting',
    'author': 'Odoo Community',
    'summary': 'Zero-python SQL reporting with DuckDB-WASM and singleflight Parquet caching.',
    'license': 'LGPL-3',

    # Description
    'description': """
# BI DuckDB WASM Engine
High-concurrency analytical reporting engine running DuckDB-WASM directly inside the browser.

## Features
- **UI SQL Builder**: Configure extract SQL and multi-view analytical queries without python restarts.
- **Dynamic Filter Params**: Automatically extracts `:param` filters for interactive frontend search bars.
- **Singleflight Parquet Cache**: Eliminates database stampedes during peak morning report spikes.
- **Multi-Company Security**: Built-in `:company_ids` validation and strict record rule isolation.
- **Client-Side Export**: Export full datasets to CSV and Parquet natively in WASM.
    """,

    # Dependencies
    'depends': ['base', 'web'],

    # Data Loading Sequence
    'data': [
        'security/ir.model.security.xml',
        'security/ir.model.access.csv',
        'data/reports_data.xml',
        'views/bi_duckdb_views.xml',
        'views/menus.xml',
    ],

    # Assets
    'assets': {
        'web.assets_backend': [
            'bi_duckdb_engine/static/src/duckdb_action.xml',
            'bi_duckdb_engine/static/src/duckdb_action.js',
        ],
    },
}
