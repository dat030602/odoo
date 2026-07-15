# -*- coding: utf-8 -*-
# Copyright 2016 ICSC

{
    "name": "Bizapps Payroll advance",
    "summary": "Payroll advance",
    "version" : "16.0.0.1",
    "category": "Payroll advance",
    "website": "https://bizapps.vn/ung-dung",
    "author": "support@bizapps.vn",
    "depends": [
        'base','hr_payroll'
    ],
    "data": [
       "views/hr_payslip_employee_views.xml",
    ],
    "application": False,
    "installable": True,
    "sequence": 1,
    'license': 'OPL-1'

}
