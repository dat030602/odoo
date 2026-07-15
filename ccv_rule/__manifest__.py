# -*- coding: utf-8 -*-
{
    'name': 'CCV Rules',
    'version': '16.0.0',
    'category': 'Tools',
    'summary': 'Module quản lý các quy tắc phân quyền cho hệ thống CCV',
    'description': "CCV Rules",
    'author': 'CCV Team',
    'website': 'https://www.ccv.vn',
    'depends': [
        'base',
        'mrp',
        'purchase',
        'sale',
        'account',
        'biz_client_ccv',
    ],
    'data': [
        'security/ir_rule_data.xml',
        'views/mrp_bom_menu.xml',
    ],
    # 'demo': [
    #     'demo/demo_data.xml',
    # ],
    # 'test': [
    #     'tests/test_ir_rules.py',
    # ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
