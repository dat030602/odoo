# -*- coding: utf-8 -*-

{
    'name': 'Bizapps - Change Password When First Login',
    'version': '16.0.0.1',
    'category': '',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','web'],
    'data': [
        'views/webclient_templates.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'biz_change_passwd_first_login/static/src/js/public_widget.js',
            'biz_change_passwd_first_login/static/src/js/popup.js',
            'biz_change_passwd_first_login/static/src/scss/frontend.scss',
        ],
    },
    'installable': True,
    'application': False,
    "license": "OPL-1",
}