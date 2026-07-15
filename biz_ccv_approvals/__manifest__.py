# -*- coding: utf-8 -*-

{
    'name': 'Bizapps - CCV Approvals',
    'version': '16.0.0.1',
    'category': 'Approvals',
    'description': "Bizapps Approvals",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['approvals', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'reports/report_action.xml',
        'reports/proposal_form_template.xml',
        'views/approval_request_views.xml',
    ],
    'installable': True,
    'application': False,
    "license": "OPL-1",
}