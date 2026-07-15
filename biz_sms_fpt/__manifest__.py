# -*- coding: utf-8 -*-
{
    # Required
    "name": "Bizapps SMS FPT",

    # Information
    "version": "16.0.1.2",
    "application": True,
    "auto_install": False,
    "installable": True,
    "summary": "Bizapps SMS FPT",
    "description": "Bizapps SMS FPT",
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "sequence": 100,
    "license": "LGPL-3",

    # Available packages
    "depends": ["base", "web", "website", "sale", "stock", "sms"],
    "data": [
        # Security
        "security/ir.model.access.csv",

        # Data
        "data/ir_cron.xml",

        # Wizard
        "wizard/sms_composer_views.xml",

        # Views
        "views/bizapps_fpt_config_view.xml",
        "views/bizapps_fpt_sms_view.xml",
        "views/bizapps_fpt_token_view.xml",
        "views/sms_fpt_log_view.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/sms_template_views.xml",
        "views/bizapps_fpt_menu.xml"
    ],
}
