# -*- coding: utf-8 -*-
{
    'name': 'Base Excel Report V2',
    'version': '19.0.2.0.0',
    'category': 'Technical',
    'summary': 'Template-based Excel report engine with Jinja-like syntax for Odoo.',
    'description': """
Base Excel Report V2
====================

A modern, template-driven Excel report engine for Odoo that eliminates the need
for hand-written row insertion and cell mapping code in child modules.

Key Features:
-------------
* Template-based: Design reports visually in Excel using Jinja-like syntax.
* Jinja-like syntax: {% for %}, {% if %}, {{ placeholder }}, and filters.
* Single hook: Child modules only implement _get_report_context() returning a dict.
* No LibreOffice dependency: Pure openpyxl + simpleeval.
* Aggregate filters: {{ lines | sum:'amount' }} generates live SUBTOTAL formulas.
* Style preservation: Row styles are copied automatically during expansion.
* Fast Mode: Skips heavy per-cell operations for large datasets.

Template Syntax:
---------------
    {{ company.name }}              Value substitution (dot-path resolution)
    {{ line.amount | fmt:'#,##0.00' }}  Number/date formatting
    {% for line in lines %} ... {% endfor %}  Loop blocks
    {% if line.amount > 1000 %} ... {% endif %}  Conditional blocks
    {{ lines | sum:'amount' }}      =SUBTOTAL(9, ...) over expanded range
    {{ lines | count:'amount' }}    =SUBTOTAL(2, ...)
    {{ lines | avg:'amount' }}      =SUBTOTAL(1, ...)
    {{ lines | max:'amount' }}      =SUBTOTAL(4, ...)
    {{ lines | min:'amount' }}      =SUBTOTAL(5, ...)

Dependencies:
-------------
    pip install openpyxl simpleeval
""",
    'author': 'Dat Nguyen',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/base_excel_report_views.xml',
        'views/ir_actions_server_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl', 'simpleeval', 'Pillow', 'requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
