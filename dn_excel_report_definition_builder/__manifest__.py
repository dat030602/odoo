# -*- coding: utf-8 -*-
{
    'name': 'Excel Report Definition Builder',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'No-code builder for defining Excel report models, fields, views and triggers.',
    'author': 'Dat Nguyen',
    'depends': ['dn_excel_report_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/excel_report_definition_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
