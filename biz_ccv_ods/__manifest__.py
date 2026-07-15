# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "BizApps - Call Center CCV",
    'version': '1.0',
    'description': """""",
    'author': "support@bizapps.vn",
    'website': "https://bizapps.vn/",
    'license': 'OEEL-1',
    'category': 'Hidden',
    'depends': ['biz_ods'],
    'data': [
        'views/biz_ods_menu.xml'
    ],
    'demo': [],
    'auto_install': False,
    'external_dependencies': {},
    'application': True,
    'assets': {},
    'installable': True,
    'maintainer': "support@bizapps.vn",
    'pre_init_hook': "",
    'post_init_hook': "",
    'uninstall_hook': "",
    'assets': {
        'web.assets_backend': [
            'biz_ccv_ods/static/src/js/user_agent.js',
        ],
    },
}


