{
    'name': 'Inventory Commitment Dashboard',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Dashboard for inventory commitments',
    'depends': ['stock', 'sale_stock', 'purchase_stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_commitment_report_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
