{
    'name': 'Bizapps - Payslip Report Excel',
    'version': '16.0.0.1',
    'summary': """
        Bizapps Payslip Report Excel
    """,
    'category': 'Payroll',
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "license": "OPL-1",
    'depends': ['hr_payroll', 'hr', 'report_xlsx'],
    'data': [
        "report/report_action.xml",
        "views/hr_salary_rule_category_views.xml",
    ],
    'installable': True,
    'auto_install': False,
}
