# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "BizApps - Web Editor",
    "category": "Hidden",
    "description": """BizApps - Odoo Web Editor widget.""",
    "depends": ["bus", "web", "web_editor"],
    "data": [],
    "assets": {
        'web_editor.assets_wysiwyg': [
            "biz_fix_web_editor/static/src/js/editor/odoo-editor/src/utils/sanitize.js"
        ]
    },
    "auto_install": False,
    "license": "LGPL-3",
}
