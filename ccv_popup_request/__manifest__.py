{
    'name': 'CCV Popup Request',
    'version': '16.0.1.0.0',
    'summary': 'Tạo đề nghị thanh toán từ Đơn mua hàng qua popup và ràng buộc đính kèm chứng từ',
    'author': 'CCV',
    'license': 'LGPL-3',
    'category': 'Purchases/Accounting',
    'depends': ['biz_payment_request', 'account', 'purchase','auto_reconcile_invoice'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
        'views/payment_request_views.xml',
        'wizards/purchase_payment_request_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
}
