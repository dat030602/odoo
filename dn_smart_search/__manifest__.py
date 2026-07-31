# -*- coding: utf-8 -*-
{
    "name": "Smart Search",
    "summary": "Global cross-model search from one box",
    "version": "1.0",
    "category": "Hidden",
    "depends": ["web"],
    "data": [
        "security/ir.model.access.csv",
        "views/smart_search_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dn_smart_search/static/src/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
