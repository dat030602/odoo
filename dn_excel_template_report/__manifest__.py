# -*- coding: utf-8 -*-
{
    'name': 'Excel Template Report - Print Odoo Records to Your Own Excel File',
    'version': '19.0.1.1.0',
    'category': 'Reporting',
    'summary': 'Design your report in Excel, upload it, and print any Odoo record to .xlsx with the original formatting kept.',
    'description': """
Excel Template Report (Odoo 19)
===============================
Upload an ``.xlsx`` file designed in Excel, mark the cells with ``${...}`` placeholders,
and print any Odoo record (Sales, Purchase, Invoice, Delivery, custom models...) to a
finished Excel file. No QWeb, no Python needed for standard reports.

Key features
------------
* Keeps cell styles, borders, merged cells, row heights, conditional formatting, images and formulas.
* Table loops: rows expand automatically for One2many / Many2many lines, and SUM formulas are extended.
* Visual builder (variables + data sources) or Python script mode for advanced cases.
* Adds a "Print" button to the target model's native Print menu in one click.
* Batch print: select many records and download a ZIP of Excel files.
* Per-template access groups and multi-company isolation.
    """,
    'author': 'Dyan',
    'images': ['static/description/banner.png'],
    'maintainer': 'Dat Nguyen',
    'support': 'dat030602@gmail.com',
    'license': 'OPL-1',
    'price': 10.00,
    'currency': 'USD',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'external_dependencies': {
        'python': ['openpyxl', 'PIL'],
    },
    'data': [
        'security/ir.model.security.xml',
        'security/ir.model.access.csv',
        'views/python_module_views.xml',
        'views/template_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}