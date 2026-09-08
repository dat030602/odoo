{
    'name': 'Stock Snapshot',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Fast stock reporting via periodic balance snapshots',
    'depends': ['stock', 'uom'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'wizard/stock_snapshot_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
