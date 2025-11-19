{
    'name': 'Misa EInvoice',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Misa EInvoice data management',
    'description': """
        Misa EInvoice data management module
        - Store invoice information
        - Manage seller/buyer information
        - Track product and service lists
    """,
    'author': 'CCV',
    'website': 'https://www.ccv.com.vn',
    'depends': ['account', 'sale_management', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_data_views.xml',
        'views/misa_map_product.xml',
        'views/misa_config_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
