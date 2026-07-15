# -*- coding: utf-8 -*-
{
    # Required
    "name": "BizApps - Notify Channels",

    # Information
    "category": "Productivity/Discuss",
    "version": "16.0.0.1",
    "application": True,
    "auto_install": False,
    "installable": True,
    "summary": "Toggle Notify Channels or Direct Message",
    "description": "Toggle Notify Channels or Direct Message",
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "sequence": 100,
    "license": "LGPL-3",

    # available packages
    "depends": ["mail", "mail_mobile"],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Data
        "data/ir_cron_views.xml",
        # Views
        "views/notify_mail_channel_views.xml"
    ],
    "assets": {
        "mail.assets_messaging": [
            "biz_notify_mail_channel/static/src/**/*",
        ],
    }
}
