{
    'name': 'Crawl Automation Invoice',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Crawl Automation Invoice data management',
    'description': """
        Crawl Automation Invoice data management module
        - Store invoice information
        - Manage seller/buyer information
        - Track bank transaction information
    """,
    'author': 'CCV',
    'website': 'https://www.ccv.com.vn',
    'depends': ['account', 'sale_management', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/gdt_einvoice_views.xml',
        'views/gdt_map_product_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
