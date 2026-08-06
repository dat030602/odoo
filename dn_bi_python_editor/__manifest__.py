# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    'name': 'BI Python Editor',

    # Short summary shown in Apps list
    'summary': 'Add Python execution support to BI SQL Editor with hot update logic',

    # Detailed description (optional when using static/description/index.html)
    'description': """
BI Python Editor for Odoo 19 extends the BI SQL Editor module to allow users
to write Python code instead of SQL queries when creating data views.

Key capabilities:
- Switch between SQL and Python execution modes per data view
- Python code runs via safe_eval with a rich import context (re, json, requests, etc.)
- Hot update logic: automatically detects field structure changes when query logic
  is modified, prompting a reset so new fields are picked up without manual intervention
- Seamless integration with the existing BI SQL Editor workflow and validation cycle
- Supports materialized views and scheduled auto-refresh for both SQL and Python modes

Workflow:
1. Create a BI SQL View and choose "Python" as the Execution Type
2. Write Python code that assigns a list of dictionaries to the variable ``result``
3. Validate the expression to auto-discover fields (must be prefixed with ``x_``)
4. Create the model and view — the Python code is executed and results are
   materialized into a database view
5. When the Python logic changes field structure, a warning appears; click
   "Reset for New Fields" to apply the updated structure
    """,

    # Author information
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',

    # Module category
    'category': 'Tools',

    # Version format: OdooVersion.ModuleVersion
    'version': '19.0.1.0.1',

    # License
    'license': 'AGPL-3',

    # Dependencies
    'depends': [
        'bi_sql_editor',
    ],

    # Data files
    'data': [
        'views/bi_sql_view.xml',
    ],

    # Static assets
    'assets': {
        'web.assets_backend': [
        ],
    },

    # Demo data
    'demo': [],

    # Installation
    'installable': True,
    'application': True,
    'auto_install': False,
}
