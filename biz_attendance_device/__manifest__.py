{
    'name': "Bizapps - Attendance Device",
    'name_vi_VN': "Tích hợp Máy chấm công Sinh trắc học",

    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    'company': 'Bizapps',
    'support': 'support@bizapps.vn',

    'summary': """""",
    'summary_vi_VN': """""",
    'description': """
- Kiểm tra tính khả dụng của máy chấm công hiện có hoặc đề xuất mua các máy chấm công sau:
+ RONALD JACK B3-C, ZKTeco K50, ZKTeco MA300, ZKTeco U580, ZKTeco T4C, ZKTeco G3, RONALD JACK iClock260
+ ZKTeco K40, ZKTeco U580, iFace402/ID, ZKTeco MB20, ZKteco IN0A-1, Uface 800
Đã bật chế độ hỗ trợ trình đọc màn hình.
 
 
    

- Kiểm tra tính khả dụng của máy chấm công hiện có hoặc đề xuất mua các máy chấm công sau:
+ RONALD JACK B3-C, ZKTeco K50, ZKTeco MA300, ZKTeco U580, ZKTeco T4C, ZKTeco G3, RONALD JACK iClock260
+ ZKTeco K40, ZKTeco U580, iFace402/ID, ZKTeco MB20, ZKteco IN0A-1, Uface 800
- Cấu hình ca làm việc 
- Tự động tính công, ngoại lệ theo dữ liệu trên máy chấm công và ca làm việc
- Xuất bảng chấm công theo nhân viên
    """,


    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Attendances',
    'version': '16.0.1.1',

    # any module necessary for this one to work correctly
    'depends': ['hr_attendance', 'hr','hr_payroll'],

    # always loaded
    'data': [
        'data/scheduler_data.xml',
        'data/attendance_state_data.xml',
        'data/mail_template_data.xml',
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'views/menu_view.xml',
        'views/attendance_device_views.xml',
        'views/attendance_state_views.xml',
        'views/device_user_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_employee_views.xml',
        'views/user_attendance_views.xml',
        'views/attendance_activity_views.xml',
        'views/finger_template_views.xml',
        'wizard/attendance_wizard.xml',
        'wizard/employee_upload_wizard.xml',
    ],
    'images' : ['static/description/main_screenshot.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 198.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
