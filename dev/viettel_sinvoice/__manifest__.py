# -*- coding: utf-8 -*-

{
    'name' : 'Vietel S-Invoice Service',
    'version' : '17.0.0.1',
    'summary': 'Integration in Odoo for Issuing E-Invoices',
    'sequence': 6,
    'description': """
    """,
    'category': '',
    'website': 'https://www.nostech.vn/',
    'images' : [],
    'depends' : ['account', 'sale', 'stock', 'vn_address_base'],
    'data': [
        # Data
        'data/data.xml',
        'data/reference_sequence.xml',
        # Security
        'security/ir.model.access.csv',
        # Views
        'wizards/cancel_sinvoice_views.xml',
        'wizards/sinvoice_edit_views.xml',
        'wizards/wizard_create_sinvoice_view.xml',
        'views/res_company_views.xml',
        'views/account_move_views.xml',
        'views/viettel_sinvoice_views.xml',
        'views/viettel_sinvoice_line_views.xml',
        'views/viettel_sinvoice_type_views.xml',
        'views/viettel_sinvoice_template_views.xml',
        'views/branch_views.xml',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
        # Reports
        'report/paper_format.xml',
        'report/report_viettel_VAT_invoice_template.xml',
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
