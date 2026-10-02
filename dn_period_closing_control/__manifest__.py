{
    'name': 'Period Closing Control',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Control Period Closings across operations',
    'depends': ['account', 'sale_stock', 'purchase_stock', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/period_lock_views.xml',
        'views/period_unlock_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
