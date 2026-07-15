# -*- coding: utf-8 -*-
{
    'name': 'Bizapps - Business Salary',
    'version': '16.0.0.1',
    'category': 'Tools',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base','hr_payroll','hr_work_entry_contract_enterprise',
        'biz_kpi_scorecard','hr_contract','hr','hr_holidays',
        'biz_payslip_advance'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_allowance.xml',
        'views/summary_from_timekeeping_machine.xml',
        'views/hr_contract.xml',
        'views/hr_employee.xml',
        'views/hr_payslip_view.xml',
        'views/collect_salary.xml',
        'views/collect_salary_line.xml',
        'views/report_telesale.xml',
        'views/report_telesale_line.xml',
        'views/config_telesale.xml',
        'views/config_telesale_line.xml',
        'views/hr_leave.xml',
        'views/kpi_period.xml',
        'views/menu_telesale.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "biz_business_salary/static/src/scss/backend.scss",
        ],
    },
    'installable': True,
    'application': True,
    "license": "OPL-1",
}
