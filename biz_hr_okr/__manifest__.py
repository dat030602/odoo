{
    'name': "BizApps - Viin HR Base",
    'name_vi_VN': "Ứng dụng HR Cơ sở",
    'summary': """
Technical module that improves HR application at technical aspects""",
    'summary_vi_VN': """
Module kỹ thuật để cải tiến các khía cạnh kỹ thuật của ứng dụng HR""",

    'description': """
Key Features
============
#. Add VAT field in employee form that is related to the corresponding partner record specified in the field Private Address
#. Improve technical link between partner and employees
#. Employee Manager Tree
#. Allow To Translate Department Information
#. And more...

Editions Supported
==================
1. Community Edition
2. Enterprise Edition

    """,
    'description_vi_VN': """
Tính năng chính
===============
#. Thêm trường VAT trên hồ sơ nhân viên, được lấy từ địa chỉ riêng tư của đối tác tương ứng
#. Tăng cường liên kết dữ liệu giữa nhân viên và địa chỉ
#. Cấu trúc các cấp quản lý của một nhân viên
#. Cho phép dịch thông tin phòng ban
#. Và các cải tiến khác

Ấn bản hỗ trợ
=============
1. Ấn bản Community
2. Ấn bản Enterprise

    """,

    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'live_test_url': "https://v14demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v14demo-vn.viindoo.com",
    'support': 'apps.support@viindoo.com',
    'category': 'Hidden',
    'version': '0.1.1',

    # any module necessary for this one to work correctly
    'depends': ['hr', 'hr_org_chart'],

    # always loaded
    'data': [
        'views/hr_job_view.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/res_partner_views.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'application': False,
    'auto_install': True,
    'price': 45.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
