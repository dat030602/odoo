{
    'name': 'Advanced ATP',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Advanced Available to Promise with prioritization',
    'depends': ['sale_stock', 'stock', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/allocation_rule_views.xml',
        'views/allocation_run_views.xml',
        'data/cron.xml',
        'data/test_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
