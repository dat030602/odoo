# -*- coding: utf-8 -*-
{
    'name': 'CCV Báo cáo',
    'summary': "CCV Báo cáo",
    'description': "",
    'category': 'Customize/Report',
    'version': '1.0',
    'author': 'CCV',
    'depends': [
        'ccv_sql',
    ],
    'sequence': 1,
    'data': [
        'views/alpha_internal_account_views.xml',
        'reports/chi_tiet_cong_no_phai_tra.xml',
        'reports/giay_bao_no.xml',
        'reports/giay_bao_co.xml',
        'reports/phieu_thu.xml',
        'reports/phieu_chi.xml',
        'reports/de_nghi_tam_ung.xml',
        'reports/chi_tiet_cong_no_phai_tra_tax.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
}
