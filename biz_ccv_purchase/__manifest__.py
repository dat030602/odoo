{
    'name': 'Bizapps - Purchase',
    'version': '1.5',
    'category': 'Inventory/Purchase',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base', 'purchase', 'purchase_stock','biz_ccv_account'],
    'data': [
        'security/ir.model.access.csv',

        'wizard/wz_purchase_create_invoice.xml',

        'reports/report_action.xml',
        "views/purchase_views.xml",
        'views/res_users_view.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}