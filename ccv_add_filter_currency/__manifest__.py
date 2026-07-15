# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'CCV Thêm Lựa chọn Tiền tệ Kế toán',
    'version': '1.3',
    'category': 'Accounting',
    'description': """CCV Thêm Lựa chọn Tiền tệ Kế toán""",
    'depends': [
        'account_reports',
    ],
    'data': [
        'views/account_report_column.xml',
        'views/search_template_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ccv_add_filter_currency/static/src/js/custom_account_reports.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
