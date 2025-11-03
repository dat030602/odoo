# -*- coding: utf-8 -*-
{
    'name': 'Vietnam Address Base',
    'summary': """The Vietnam Address Base module is an extension for the Odoo system designed to provide a comprehensive database of addresses in Vietnam.""",
    'author': 'Dat Nguyen Van',
    'license': 'LGPL-3',
    'category': 'Extra Tools',
    'version': '17.0.1.0',
    'support': 'dat030602@gmail.com',
    'depends': ['base', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_country_district_views.xml',
        'views/res_country_ward_views.xml',
        'views/res_country_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml'
    ],
    'images': ['static/description/thumbnail.png'],
    'application': False,
    'installable': True,
}
