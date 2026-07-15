# -*- coding: utf-8 -*-
{
    'name': "purchase_customs_infomation_ccv",
    'summary': """
        Base for storing customs information (container, seal, ...)
    """,
    'description': """
        Base for storing customs information (container, seal, ...)
    """,
    'author': "Leonix",
    'website': "https://leonix.vn",
    'category': 'Purchase',
    'version': '16.0',
    'depends': ['purchase','stock','purchase_requisition','sale_management', 'sale_stock', 'stock_landed_costs', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_product_views.xml',
        'views/purchase_order_views.xml',
        'views/transport_ticket_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'maintainers': ['leonix'],
}
