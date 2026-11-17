{
    'name': 'Currency Rate Datetime',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Currencies',
    'summary': 'Allows multiple currency exchange rates per day with datetime precision',
    'description': """
Currency Rate Datetime
======================
This module enhances Odoo's currency rate management by converting the currency rate
date field into a Datetime field.

Key Features:
-------------
* Support for multiple exchange rates within the same day.
* Unique exchange rate constraint per second per currency and company.
* Accurate rate lookup based on exact datetime or fallback to date.
* Company timezone conversion for accurate datetime handling.
* Pre/Post installation and uninstallation hooks for smooth data migration.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'views/res_currency_rate_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
}
