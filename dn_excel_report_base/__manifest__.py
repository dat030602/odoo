{
    'name': 'Excel Report Base',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Base module for creating and managing Excel reports in Odoo',
    'description': """A base module to create and manage Excel reports in Odoo using a configuration-based approach instead of coding.""",
    'depends': ['mail', 'report_xlsx'],
    'data': [
        'views/excel_report_views.xml',
    ],
    'installable': True,
}
