{
    'name': "Viettel S-Invoice V2",
    'summary': """ Kết nối hóa đơn điện tử Viettel """,
    'description': """
        - Module sẵn có, yêu cầu thêm tính phí
    """,
    'category': 'API Viettel S-Invoice',
    'version': '16.0',
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "license": "OPL-1",
    "company": 'Bizapps',
    "support": 'support@bizapps.vn',
    "data": [
        'data/data.xml',
        'data/item_type_mapping_data.xml',
        'data/cron.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/sinvoice_cancel.xml',
        'wizard/sinvoice_edit.xml',
        'view/product_template.xml',
        'view/res_company.xml',
        'view/res_partner_view.xml',
        'view/account_invoice_view.xml',
        'view/viettel_sinvoice_view.xml',
        'view/log_request_sinvoice_view.xml',
        'view/viettel_sinvoice_config_view.xml',
        'view/viettel_sinvoice_item_type_set_view.xml',
        'view/viettel_sinvoice_type_view.xml',
        'view/sale_order_views.xml',
        'view/account_tax_view.xml'
    ],
    "depends": [
        'base', 
        'base_setup', 
        'account', 
        'account_accountant', 
        'biz_vn_address',
        'sale_management'
    ],
    'assets': {
        'web.assets_backend': [
            "biz_viettel_sinvoice_v2/static/src/scss/*.scss",
            "biz_viettel_sinvoice_v2/static/src/xml/*.xml",
            "biz_viettel_sinvoice_v2/static/src/js/*.js",
        ]
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}