# -*- coding: utf-8 -*-
{
    'name': "BizApps - OKR",
    'name_vi_VN': "OKR",

    'summary': """
Help you implement OKR in your organizations""",

    'summary_vi_VN': """
Giúp bạn triển khai hiệu quả hệ thống quản trị doanh nghiệp với OKR""",

    'description': """

What it does
============
* OKR (Objectives & Key Results) is a goal-setting framework for defining and linking objectives of the enterprise, departments and employees to specific key outcomes.
* OKRs help enterprises focus on the most important goals, combine all resources to achieve that goal. OKR also helps each individual understand their contribution to the common goal and measure all activities.
* This application helps you focus on your objectives and measure them by key results.

Key Features
============
* OKR Definitions

   * Define company objectives for year, quarter
   * Define company departments' objectives which are also key results of the company's objectives
   * Define employee's objectives which are also key results of the departments' objectives

* Measure objective achievement automatically from its key result's points
* Visualize objectives and key results hierarchy with OKR chart
* Ready for other applications to extend (e.g. Projects, Timesheet, Gamification, etc)

Supported Editions
==================
1. Community Edition
2. Enterprise Edition

    """,

    'description_vi_VN': """

Mô tả
=====
* OKR (Objectives & Key Results - Mục tiêu & Kết quả then chốt) là một hệ thống xác định mục tiêu giúp liên kết mục tiêu của công ty, của phòng ban và mục tiêu cá nhân tới các kết quả then chốt cụ thể. 
* OKR giúp doanh nghiệp tập trung vào những mục tiêu quan trọng nhất, cộng hưởng mọi nguồn lực để đạt được mục tiêu, giúp mỗi cá nhân hiểu rõ đóng góp của mình cho mục tiêu chung và định lượng hóa mọi hoạt động.
* Ứng dụng này cho phép bạn triển khai hệ thống quản trị doanh nghiệp với OKR, tập trung vào các mục tiêu (objectives) và đo lường chúng bằng các kết quả then chốt (key results)

Tính năng nổi bật
=================
* Khởi tạo OKR

   * Định nghĩa các mục tiêu của công ty theo năm, theo quý
   * Định nghĩa các mục tiêu của các phòng ban, cũng đồng thời là các kết quả then chốt của công ty.
   * Định nghĩa các mục tiêu của từng nhân viên, cũng đồng thời là các kết quả then chốt của phòng ban của họ.

* Đo lường tự động tiến độ hoàn thành các mục tiêu dựa trên mức độ hoàn thành của các kết quả then chốt của chúng
* Trực quan hóa cấu trúc phả hệ của các mục tiêu và kết quả then chốt thông qua sơ đồ OKR
* Sẵn sàng cho các ứng dụng khác tích hợp và mở rộng tính năng (vd: Dự án, Chấm công, Gamification, v.v.)

Ấn bản được Hỗ trợ
==================
1. Ấn bản Community
2. Ấn bản Enterprise

    """,

    'author': 'support@bizapps.vn',
    'website': "https://www.bizapps.vn",
    'category': 'Human Resources/OKR',
    'version': '0.1.2',
    'depends': ['hr', 'biz_org_chart', 'biz_hr_okr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/okr_node_views.xml',
        'views/root_menu.xml',
        'views/hr_employee_public_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_setting.xml',
    ],
    'images': [
    	'static/description/main_screenshot.png'
    	],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 99.9,
    'subscription_price': 4.97,
    'currency': 'EUR',
    'license': 'OPL-1',
}
