# -*- coding: utf-8 -*-

{
    'name': 'Bizapps - Sign',
    'version': '1.0',
    'category': 'Sales/Sign',
    'summary': '',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base', 'sign'],
    'data': [
    #    'wizard/sign_send_request_views.xml',
       'views/sign_template_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'web.assets_backend': [
        'biz_sign/static/src/js/*',
    ],
    'web.assets_frontend': [
        'biz_fonts/static/src/fonts/SVN-Gilroy/SVN-Gilroy.css',
        ],
}
