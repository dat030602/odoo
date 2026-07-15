# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    # Basic
    'name': 'BizApps - Hide Menu',
    'version': '1.0',
    'summary': "Restrict Menu Items from Specific Users",
    'description': """Restrict Menu Items from Specific Users""",
    'author': "support@bizapps.vn",
    'website': "https://bizapps.vn/",
    'license': 'LGPL-3',
    'category': 'Hidden',
    'depends': [],
    'data': [
        # Security
        # Data
        # Wizard
        # "wizard/sign_send_request_views.xml",
        # Reports
        # Views
        "views/res_users_views.xml",
    ],
    'demo': [],
    'auto_install': False,
    'external_dependencies': {},
    'application': False,
    'assets': {},
    'installable': True,
    'maintainer': "support@bizapps.vn",
    'pre_init_hook': "",
    'post_init_hook': "",
    'uninstall_hook': "",

    # Advanced

}
