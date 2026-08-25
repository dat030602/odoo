{
    'name': 'Report PDF Merger',
    'version': '19.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Merge additional PDF files (cover/appendix) into Odoo PDF reports',
    'description': """
Report PDF Merger
=================
This module allows users to attach additional PDF files to any QWeb PDF report.
The attached files can be positioned either at the beginning (cover pages) or
at the end (appendix pages) of the generated report.

Features:
- Drag-and-drop reordering via sequence field with handle widget
- Separate configuration for prepend (cover) and append (appendix) files
- Uses Odoo's built-in PDF merge tool (odoo.tools.pdf.merge_pdf)
- Clean separation of concerns with a dedicated line model
""",
    'author': 'DN Solutions',
    'website': 'https://www.dnsolutions.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_actions_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}