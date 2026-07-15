# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bizapps - Sổ tiền gửi ngân hàng CCV (S08-DN)',
    'version': '16.0.0.1',
    'summary': 'Sổ tiền gửi ngân hàng (S08-DN) CCV',
    'description': """
        Sổ tiền gửi ngân hàng (S08-DN) CCv
    """,
    'category': 'Accounting',
    "website": "https://www.bizapps.vn",
    'author': 'support@bizapps.vn',
    'depends': ['biz_bank_deposit_book','biz_manual_currency_exchange_rate'],
    'data': [
        'reports/bank_deposit_pdf_view.xml',
        'views/bank_deposit_book_view.xml'
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
    'auto_install': False,
}
