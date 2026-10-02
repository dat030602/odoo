{
    'name': 'Credit Sale Control',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Control Credit limits in Sales',
    'depends': ['sale_management', 'account', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/credit_release_log_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
