# -*- coding: utf-8 -*-

{
    'name': 'Bizapps - Account CCV',
    'version': '1.0',
    'category': 'Account CCV',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base', 'sale', 'base_geolocalize', 'biz_field_image_preview', 'sale_management', 'contacts',
                'sales_team', 'crm', 'product', 'account','biz_vn_address', 'account_reports'],
    'data': [
        "data/ir_cron.xml",
        'data/account_report_data.xml',

        "security/ir.model.access.csv",
        "security/type_contact_sercurity.xml",

        'views/partner_view.xml',
        'views/contact_views.xml',
        'views/contact_account.xml',
        'views/res_users_views.xml',
        'views/crm_team_view.xml',
        'views/product_template_views.xml',
        'views/res_partner_hide_fields_views.xml',
        'views/sale_menus.xml',
        'views/account_payment.xml',
        'views/account_move_view.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'biz_ccv_account/static/src/search/**/*',
            'biz_ccv_account/static/src/components/**/*',
        ],
    },
}
