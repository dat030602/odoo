# -*- coding: utf-8 -*-
{
    'name': 'Bizapps Tree Management',
    'version': '16.0',
    'category': 'General',
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'license': 'AGPL-3',
    'description': """ Tree Management """,
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        
        'views/tree_management_view.xml',
        'views/plant_type_view.xml',
        'views/area_view.xml',
        'views/plant_view.xml',
        'views/fertilization_process_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
