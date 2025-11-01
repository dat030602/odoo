# -*- coding: utf-8 -*-
{
    'name': "Vinh Hy E-Invoice Service",

    'summary': """Integration in Odoo for Issuing Vinh Hy E-Invoices""",

    'description': """
    """,

    'author': "Vmax ERP Consulting",
    'website': "https://erp.vmax.vn/",
    'category': '',
    'version': '1.0',
    'depends': ['base', 'account', 'stock', 'sale'],

    # always loaded
    'data': [
        # security
        'security/ir.model.access.csv',
        # data
        'data/data.xml',
        'data/ir_server_action.xml',
        # views
        'wizard/cancel_einvoice_views.xml',
        # 'wizard/adjust_einvoice_views.xml',
        'views/res_company_views.xml',
        'views/vat_product_template_views.xml',
        'views/vinhhy_einvoice_views.xml',
        'views/vinhhy_einvoice_type_views.xml',
        'views/vinhhy_einvoice_template_views.xml',
        'views/account_move_views.xml',
        'views/einvoice_tax_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/partner_vat_views.xml',
        'views/menu.xml'
    ],
    
    'sequence': 6,
    'installable': True,
    'application': True,
}
