# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "CCV: Lệnh sản xuất",
    "version": "1.3",
    "category": "",
    "description": """Lệnh sản xuất""",
    "depends": [
        "ccv_custom_field",
    ],
    "data": [
        'data/parameter.xml',
        'data/server.xml',
        'data/mail_activity_data.xml',
        'security/ir.model.access.csv',
        'views/mrp.xml',
        'views/stock_warehouse_orderpoint.xml',
        'wizards/create_orderpoint_wizard.xml',
        'wizards/mrp_production_consignment_wizard_views.xml',
        'views/stock_picking_views.xml',
    ],
    "installable": True,
    "license": "LGPL-3",
}
