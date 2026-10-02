{
    'name': 'Credit Delivery Control',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Control Credit limits in Delivery',
    'depends': ['dn_credit_sale_control', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/credit_release_wizard_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
