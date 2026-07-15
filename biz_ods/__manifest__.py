# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "BizApps - Call Center ODS",
    'version': '1.0',
    'description': """
- Save the call list.
- Save the recording file in the contact corresponding to the incoming and outgoing phone numbers.
    """,
    'author': "support@bizapps.vn",
    'website': "https://bizapps.vn/",
    'license': 'OEEL-1',
    'category': 'Productivity/ODS',
    'depends': ['base', 'web', 'base_setup', 'contacts', 'voip',
                'biz_audio_field'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/biz_ods_groups.xml',
        'security/biz_ods_security.xml',
        # Data
        'data/ir_cron_data.xml',
        # Wizard
        'wizard/biz_ods_sync_wizard_views.xml',
        # Views
        'views/res_config_settings_views.xml',
        'views/biz_ods_logs_views.xml',
        'views/biz_ods_extension_views.xml',
        'views/biz_ods_call_history_views.xml',
        'views/res_partner_views.xml',
        # 'views/res_users_views.xml',
        'report/biz_ods_report_views.xml',
        'views/ods_wehook_view.xml',
        'views/biz_ods_menus.xml'
    ],
    'demo': [],
    'auto_install': False,
    'external_dependencies': {
    },
    'application': False,
    'assets': {
        'web.assets_backend': [
            # JS
            'biz_ods/static/src/js/phone_call_tab.js',
            'biz_ods/static/src/js/call_history_list_renderer.js',
            'biz_ods/static/src/js/call_history_form_renderer.js'
        ],
    },
    'installable': True,
    'maintainer': "support@bizapps.vn",
    'pre_init_hook': "",
    'post_init_hook': "",
    'uninstall_hook': "",
}


