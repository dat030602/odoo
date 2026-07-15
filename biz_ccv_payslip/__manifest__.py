{
    'name': 'Bizapps - CCV Payslip',
    'version': '1.5',
    'category': 'HR',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','hr_payroll','biz_payslip_advance'],
    'data': [
        'reports/report_action.xml',
        'reports/hr_payslip_pdf_template.xml',
        'views/hr_payslip_view.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}