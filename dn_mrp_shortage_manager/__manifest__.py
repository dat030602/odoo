{
    'name': 'MRP Shortage Manager',
    'author': 'Dyan',
    'images': ['static/description/banner.png'],
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Manage Material Shortages in Manufacturing',
    'depends': ['mrp', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_production_views.xml',
        'views/mrp_shortage_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
