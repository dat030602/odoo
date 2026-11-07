# -*- coding: utf-8 -*-
{
    "name": "Vietnam Address Management (v1)",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "summary": "3-Tier Vietnamese Administrative Address Structure (Provinces, Districts, Wards) with Open API v1 Sync",
    "description": """
Vietnam Administrative Address Management (v1)
==============================================
Implements the 3-tier Vietnamese administrative address structure:
- Provinces / Cities (res.country.state)
- Districts (res.country.district)
- Wards / Communes (res.country.ward)

Features:
- Dynamic onchange reactivity and domain filtering across Country -> Province -> District -> Ward.
- Partner and Company bidirectional synchronization.
- Vietnamese address format for base.vn: %(street)s\\n%(ward_name)s, %(district_name)s\\n%(state_name)s\\n%(country_name)s.
- Computed full address (full_address_vi).
- Direct Open API v1 synchronization via system parameter `dn_vn_address.api_url`.
""",
    "author": "MJB Solutions",
    "license": "LGPL-3",
    "depends": ["base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "data/res.country.state.csv",
        "data/res_country_data.xml",
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
