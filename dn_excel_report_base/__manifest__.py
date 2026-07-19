# -*- coding: utf-8 -*-
{
    'name': 'Dynamic Excel Report Base',
    'version': '19.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Framework to generate dynamic Excel Reports based on UI configuration',
    'description': """
        This is the Base module for the Excel Report Builder[cite: 1].
        It provides the core Engine, Formats, Functions, Columns, and Signatures configuration models.
    """,
    'author': 'Your Name',
    'depends': ['mail', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'views/excel_report_column.xml',
        'views/excel_report_signature.xml',
        'views/excel_report_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}