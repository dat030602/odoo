{
    'name': 'Shopee Connector',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'CCV Marketplace Connector',
    'description': """
        Module for managing Marketplace connections
    """,
    'author': 'CCV',
    'website': 'https://www.ccv.vn',
    'depends': ['sale_management','stock_account'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        # 'data/cron.xml',
        'views/shopee_response.xml',
        'views/shopee_connector.xml',
        'views/shopee_product_mapping.xml',
        'views/templates/auth_templates.xml',
        'views/menu_views.xml',
    ],
    'i18n': [
        'i18n/vi.po',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
