# -*- coding: utf-8 -*-
{
    'name': 'Vietnamese XML Invoice Import',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Import Vietnamese electronic invoice XML files',
    'description': """
        Vietnamese XML Invoice Import Module
        =====================================
        
        This module allows importing Vietnamese electronic invoice XML files into Odoo.
        
        Features:
        - Upload multiple XML files
        - Parse Vietnamese e-invoice XML format
        - Store invoice data in staging models
        - Two-step confirmation workflow
        - Automatic partner detection by VAT
        - Fuzzy product matching
        - Tax mapping
        - Create Account Move records
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/xml_invoice_import_views.xml',
        'views/xml_invoice_upload_wizard_views.xml',
        'views/xml_invoice_create_move_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'l10n_vn_invoice_import/static/src/js/xml_invoice_upload.js',
    #     ],
    # },
    'python_requires': '>=3.8',
    'external_dependencies': {
        'python': [
            'xmltodict',
            'rapidfuzz',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
