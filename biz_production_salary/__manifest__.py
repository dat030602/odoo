# -*- coding: utf-8 -*-
{
    'name': 'Bizapps - Production Salary',
    'version': '16.0.0.1',
    'category': 'Tools',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': [
        'base','product','hr','stock','mrp','hr_work_entry_contract_enterprise',
        'hr_payroll','biz_business_salary','stock_barcode','report_xlsx','biz_to_stock_backdate', 'trp_approve'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/parameter.xml',

        'wizard/popup_print_salary_bx_wizard.xml',

        'report/report_salary_by_production_template.xml',
        'report/report_view.xml',

        'views/menu_item.xml',
        'views/hr_employee.xml',
        'views/stock_picking.xml',
        'views/mrp_production.xml',
        'views/mrp_bom.xml',
        'views/enter_daily_work_output_other.xml',
        'views/summary_output_spreadsheet.xml',
        'views/total_amount_received_byday.xml',
        'views/final_total.xml',
        'views/employee_enjoys.xml',
        'views/summary_output_daily_work.xml',
        'views/change_manual_worker_coefficient_byday.xml',
        'views/config_classification.xml',
        'views/employee_classification.xml',
        'views/product_template.xml',
        'views/day_labor.xml',
        'views/stock_warehouse.xml',
        'views/advance_salary_summary.xml',
        'views/hr_payslip_run.xml',
        'views/hr_payslip.xml',
    ],
    'installable': True,
    'application': True
    ,
    "license": "OPL-1",
    'assets': {},
}
