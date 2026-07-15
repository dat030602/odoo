# -*- coding: utf-8 -*-
{
    "name": "Bizapps - Update inventory again",
    "version": "16.0.0.1",
    "category": "Extra Tools",
    'author': "support@bizapps.vn",
    'website': "http://www.bizapps.vn/ung-dung",
    "installable": True,
    'license': "OPL-1",
    "auto_install": False,
    "depends": [
        "base",'stock'
    ],
    "data": [
        'data/cron.xml',
        'views/product_view.xml'
    ],
    "summary": "Update inventory again",
    "description": """
       Update inventory again
""",
}