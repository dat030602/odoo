# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    # Basic
    'name': 'BizApps - Sign Sequence',
    'version': '1.0',
    'summary': "If installed, the document have to sign in sequence(one after the other)",
    'description': """If installed, the document have to sign in sequence(one after the other)""",
    'author': "support@bizapps.vn",
    'website': "https://bizapps.vn/",
    'license': 'LGPL-3',
    'category': 'Hidden',
    'depends': ['sign'],
    'data': [
        # Security
        "security/security.xml",
        # Data
        # Wizard
        # "wizard/sign_send_request_views.xml",
        # Reports
        # Views
        "views/sign_request_views.xml",
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
