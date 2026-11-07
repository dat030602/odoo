# -*- coding: utf-8 -*-
{
    "name": "Vietnam Address Administrative Reform (NQ60 / v2)",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "summary": "2-Tier Vietnam Administrative Address Architecture (NQ60 Reorganization) with Open API v2 Sync",
    "description": """
Vietnam Address Administrative Reform (NQ60 / v2)
=================================================
Implements the 2-tier administrative reorganization under Resolution 60/NQ-CP:
- Country -> Province (34 consolidated units) -> Ward (3,321 consolidated units).
- Districts are archived and hidden from UI address forms.
- Re-defines address format for base.vn to:
  %(street)s\\n%(ward_name)s\\n%(state_name)s\\n%(country_name)s
- Data merging tools: map_with_state_ids, map_with_ward_ids, action_merge_state_nq60(), action_merge_ward_nq60().
- Direct API Sync v2 via system parameter `dn_vn_address_nq60.api_url`.
""",
    "author": 'Dyan',
    'images': ['static/description/banner.png'],
    "license": "LGPL-3",
    "depends": ["base", "dn_vn_address"],
    "data": [
        "data/res_country_data.xml",
        "data/res_country_state_data.xml",
        "data/ir_config_parameter_data.xml",
        "data/ir_cron_data.xml",
        "views/res_country_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
