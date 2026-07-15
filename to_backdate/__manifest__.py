{
    'name': "Backdate Operations Access Rights",
    'summary': """
Access group for backdate operations""",
    'summary_vi_VN': """
    	""",
    'description': """
This module is intended for other backdate-related modules to extend such as Stock Transfers Backdate, Inventory Backdate, Sales Confirmation Backdate, etc

Editions Supported
==================
1. Community Edition
2. Enterprise Edition
    """,

    'description_vi_VN': """
Module này là module cơ sở để các module liên quan đến backdate có thể kế thừa.

Ấn bản được Hỗ trợ
==================
1. Ấn bản Community
2. Ấn bản Enterprise

    """,

    'author': 'support@bizapps.vn',
    'website': 'www.bizapps.vn',
    'support': "support@bizapps.vn",
    'category': 'Hidden',
    'version': '15.0',

    'depends': ['base'],

    'data': [
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'wizard/abstract_inventory_backdate_wizard_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}