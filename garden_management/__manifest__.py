# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "Garden Management",
    "version": "1.3",
    "category": "Garden Management",
    "description": """Garden Management""",
    "depends": ["product", "knowledge"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "data/parameter.xml",
        "views/garden_area.xml",
        "views/garden_care.xml",
        "views/garden_fertilizer.xml",
        "views/garden_fertilizer_usage.xml",
        "views/garden_history.xml",
        "views/garden_plan.xml",
        "views/garden_proportion.xml",
        "views/garden_stage.xml",
        "views/garden_tree.xml",
        "views/garden_area_kanban.xml",
        "views/menu.xml",
    ],
    "assets": {},
    "installable": True,
    "license": "LGPL-3",
}
