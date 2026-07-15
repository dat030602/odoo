# -*- encoding: utf-8 -*-
{
    "name": "Bizapps - Nâng cấp tính năng phiếu lương",
    "category": "Human Resource",
    "version": "16.0.0.1",
    
    "summary": "Module cung cấp giải pháp phụ cấp, giảm trừ, ngày công cho phần lương",
    "description": "Module cung cấp giải pháp phụ cấp, giảm trừ, ngày công cho phần lương",
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "website": "https://bizapps.vn/ung-dung",
    "license": "OPL-1",
    "depends": ['hr',
        "hr_payroll",
        'biz_hr_payslip',
        'biz_payslip_pdf_report',
        'biz_payslip_excel_report'
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',

        'data/data_view.xml',
        'data/hr.allowance.csv',
        'data/hr.type.working.day.csv',
        'data/mail_template.xml',

        'views/menuitem.xml',
        'views/hr_allowances_view.xml',
        'views/hr_deduction_view.xml',
        'views/hr_payroll_update_view.xml',
        'views/hr_working_day_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_employee_views.xml',
        'views/hr_payslip.xml',
        'views/config_salary_insurence_union_dues.xml',
        # 'views/res_setting_view.xml',

        'report/payslip_report_pdf.xml'
    ],
    "application": True,
    "auto_install": False,
    "installable": True,
    'post_init_hook': 'post_init_import_csv'
}
