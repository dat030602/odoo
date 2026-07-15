{
    'name': 'PDF  payslip and email payslip',
    'version': '16.0.0.1',
    'summary': """
    The module provides the ability to print PDF pay slips and send pay slips by email
    """,
    'category': 'Payroll',
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "license": "OPL-1",
    'depends': ['hr_payroll', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payslip_views.xml',
        # view
        'views/hr_salary_rule_view.xml',
        'views/hr_payslip_view.xml',
        'views/hr_salary_rule_category_view.xml',
        'views/hr_employee_view.xml',
        'views/res_setting_view.xml',
        # report
        'report/report_action.xml',
        'report/payslip_report_pdf.xml'
    ],
    'installable': True,
    'auto_install': False,
    'qweb': [
        "static/src/xml/report.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'biz_payslip_pdf_report/static/src/js/report.js'
        ]
    },
}
