{
    'name': "Vietnam - HR Employee Identification (Citizen ID/ID Card)",
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': "Citizen Identity Card (CCCD) and Identity Card (CMND) management for Vietnamese employees",
    'description': """
Vietnam - HR Employee Identification (Citizen ID/ID Card)
=========================================================
This module extends the standard Employee model (hr.employee) to manage Vietnamese identification documents:
* Support for Citizen Identity Card (CCCD/12 digits) and Identity Card (CMND/9 digits).
* Storage for Issue Date, Expiry Date, Issuing Place, and Front/Back card images.
* Format validations (regex for 12/9 digits), date chronological integrity, and uniqueness across active employees.
* Fast search by ID Card Number in employee search view.
* Automatic sync to standard identification_id if empty.
    """,
    'author': "Dat Nguyen",
    'license': 'LGPL-3',
    'depends': ['hr'],
    'data': [
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
