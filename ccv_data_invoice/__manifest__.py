{
    'name': 'CCV Data Invoice',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Quản lý dữ liệu hóa đơn điện thử',
    'description': """
        Module quản lý dữ liệu hóa đơn được import từ hóa đơn điện tử
        - Lưu trữ thông tin hóa đơn
        - Quản lý thông tin người bán/người mua
        - Theo dõi danh sách hàng hóa dịch vụ
        - Import dữ liệu từ file XML
    """,
    'author': 'CCV',
    'website': 'https://www.ccv.com.vn',
    'depends': ['base', 'account', 'product', 'purchase_stock'],
    'data': [
        'data/server.xml',
        'security/ir.model.access.csv',
        'wizard/stock_move_wizard.xml',
        'views/invoice_data_views.xml',
        'views/import_wizard_views.xml',
        'views/wizard_views.xml',
        'views/mapping_data_product.xml',
        'views/menu_views.xml',
        'views/account_move.xml',
        'views/purchase_order.xml',
        'wizard/purchase_order_invoice_data_wizard.xml',
        'wizard/account_move_update_invoice_info_wizard.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
