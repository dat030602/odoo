# -*- coding: utf-8 -*-

{
    'name': 'Bizapps - Discuss',
    'version': '1.5.8',
    'category': 'Productivity/Discuss',
    'summary': 'Chat, mail gateway and private channels',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base', 'mail', 'biz_hide_menu'],
    'data': [
        'data/res_users_data.xml',
        'security/mail_security.xml',
        'security/ir.model.access.csv',

        # 'data/all_channel_data.xml',

        'views/res_config_settings_views.xml',
        'views/mail_channel_views.xml',
        'views/current_user_pinned_channel_views.xml',
        'views/partner_seen_channel_views.xml',
        'views/res_users_views.xml',
        'views/all_channel_views.xml'
    ],
    'installable': True,
    'application': True,
    'assets': {
        # 'mail.assets_core_messaging': [
        #     'biz_mail/static/src/model/*.js',
        # ],
        'mail.assets_messaging': [
            'biz_mail/static/src/models/*.js',
        ],
        'mail.assets_discuss_public': [
            'biz_mail/static/src/components/*/*',
        ],
        'web.assets_backend': [
            'biz_mail/static/src/components/*/*.js',
            'biz_mail/static/src/components/*/*.scss',
            'biz_mail/static/src/components/*/*.xml',

            'biz_mail/static/src/views/*.js',
            'biz_mail/static/src/views/*.xml',
            # 'biz_mail/static/src/views/*.scss',
        ],
    },
    
    'license': 'LGPL-3',
}
