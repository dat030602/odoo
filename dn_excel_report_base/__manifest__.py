# -*- coding: utf-8 -*-
{
    'name'        : 'Base Excel Report',
    'version'     : '19.0.1.0.0',
    'category'    : 'Technical',
    'summary'     : 'Base framework for template-based Excel report generation.',
    'description' : """
Base Excel Report Framework
============================

Provides a reusable, inheritable pipeline for generating Excel reports
from pre-designed templates stored as Odoo ir.attachment records.

Key Features:
-------------
* Template-based: Design reports visually in Excel, not in Python code.
* Marker-driven: Uses <TABLE_START> cell marker to locate insertion point.
* Placeholder replacement: {{KEY}} syntax for dynamic Header/Footer values.
* Auto row insertion: Inserts the exact number of rows needed, preserving
  all content above and below the table.
* Style copy: Propagates font, border, fill, alignment from the template row
  to all newly inserted rows (Normal Mode).
* Auto-fit columns: Adjusts column widths based on actual data length.
* Fast Mode: Skips heavy per-cell operations for datasets exceeding
  the configured threshold, ensuring server stability at scale.
* Fully inheritable: Child modules only override 3-4 hook methods.

Dependencies:
-------------
    pip install openpyxl
    """,
    'author'   : 'Dat Nguyen',
    'depends'  : ['base', 'web'],
    'data'     : [
        'security/ir.model.access.csv',
        'views/base_excel_report_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'installable'  : True,
    'application'  : False,
    'auto_install' : False,
    'license'      : 'LGPL-3',
}
