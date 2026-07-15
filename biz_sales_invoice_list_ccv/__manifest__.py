# -*- coding: utf-8 -*-
{
    'name': 'Bizapps - Sales Invoice List CCV',
    'version' : '16.0.0.1',
    'description': '',
    'category': 'Extra Tools',
    'website': "https://bizapps.vn/ung-dung",
    'author': "support@bizapps.vn",
    'company': 'Bizapps',
    "license": "OPL-1",
    'depends': ['biz_purchase_invoices_list_ccv','biz_viettel_sinvoice_v2','stock_account'],
    'data': [
        'security/ir.model.access.csv',

        'report/report_view.xml',

        'wizard/wizard_sale_invoicelist_view.xml',

        'views/sale_invoices_list_view.xml',
        'views/menu.xml',
        'views/account_move_view.xml',
        'views/account_tax_view.xml',
        'views/account_view.xml',
        'views/product_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
