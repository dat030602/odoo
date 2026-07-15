# -*- coding: utf-8 -*-
{
    'name': 'Bizapps VN Address',
    'version': '16.0',
    'category': 'General',
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'license': 'AGPL-3',
    'description': """ Address vietnam """,
    'depends': ['base', 'contacts', 'l10n_vn'],
    'data': [
        'security/ir.model.access.csv',

#        'data/res.country.state.csv',
 #       'data/res.country.district.csv',
  #      'data/res.country.wards.csv',
        'data/cron_view.xml',

        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/update_address_view.xml'
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
