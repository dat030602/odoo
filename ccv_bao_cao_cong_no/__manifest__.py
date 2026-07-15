# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'CCV Báo cáo Công nợ',
    'version': '1.3',
    'category': 'Accounting',
    'description': """CCV Báo cáo Công nợ""",
    'depends': [
        'ccv_bao_cao',
        'biz_viettel_sinvoice_v2',
    ],
    'data': [
        'data/parameter.xml',
        'security/ir.model.access.csv',
        'reports/tong_hop_cong_no_phai_tra_nt.xml',
        'reports/tong_hop_cong_no_phai_thu_nt.xml',
        'reports/tong_hop_cong_no_phai_tra.xml',
        'reports/tong_hop_cong_no_phai_thu.xml',
        'reports/chi_tiet_cong_no_phai_tra_nt.xml',
        'reports/chi_tiet_cong_no_phai_thu_nt.xml',
        'reports/chi_tiet_cong_no_phai_thu.xml',
        'reports/chi_tiet_cong_no_phai_tra.xml',
        'reports/bao_cao_ccv_report.xml',
        'views/view_tree.xml',
        'views/report_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
