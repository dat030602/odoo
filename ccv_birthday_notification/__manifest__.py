# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CCV Birthday Notification',
    'version': '1.0',
    'summary': 'Send birthday notifications',
    'category': 'Contact',
    'author': 'Dat Nguyen CCV',
    'website': 'https://ccv.digital/',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
