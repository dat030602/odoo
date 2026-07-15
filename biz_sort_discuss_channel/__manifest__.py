{
    # Required
    "name": "BizApps - Sort Last Action Discuss As Channels",

    # Information
    "category": "Productivity/Discuss",
    "version": "16.0.0.1",
    "application": False,
    "auto_install": False,
    "installable": True,
    "summary": "Orderby last action discuss as channels",
    "description": "Orderby last action discuss as channels",
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "sequence": 100,
    "license": "OPL-1",

    # Available packages
    "depends": ["mail"],
    "assets": {
        "mail.assets_messaging": [
            "biz_sort_discuss_channel/static/src/**/*",
        ],
    },
}