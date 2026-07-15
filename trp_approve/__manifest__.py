# -*- coding: utf-8 -*-
{
    'name': 'Cấu hình phê duyệt',
    'description': """
        - Thiết lập các cấu hình phê duyệt áp dụng cho các module phụ thuộc
    """,
    'category': 'Technical setting',
    'version': '1.0',
    'author': 'HaiTran',

    'version': '1.0',
    'depends': [
        'account_accountant',
        'hr_expense',
        'hr',
                ],

    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_views.xml',
        'data/trp_approve_config_data.xml',
        'views/trp_approve_config.xml',
        'views/trp_approve_history_view.xml',
        'views/alpha_internal_account_views.xml',
        'views/hr_expense_sheet_views.xml',
        'wizard/trp_approve_config_reason.xml'
    ],
}
