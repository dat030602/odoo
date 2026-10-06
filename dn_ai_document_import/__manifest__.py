# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "AI Document Import (OCR)",
    "summary": "Import sales and documents using Odoo 19 AI multimodal models",
    "version": "19.0.1.0.0",
    "category": "Productivity/Artificial Intelligence",
    "author": "Antigravity",
    "license": "OEEL-1",
    "depends": [
        "sale",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/dn_ai_import_template_data.xml",
        "views/res_config_settings_views.xml",
        "views/dn_ai_import_template_views.xml",
        "wizard/dn_ai_import_wizard_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
