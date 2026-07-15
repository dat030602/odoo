{ 
    "name": "Purchase to Delivery",
    "summary": "Create delivery orders from purchase orders, one per container number.",
    "version": "16.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "Your Company",
    "website": "",
    "depends": ["purchase", "stock", "purchase_customs_infomation_ccv", "biz_ccv_sale"],
    "data": [
        "views/stock_picking_views.xml",
        "views/delivery_picking_wizard_views.xml",
        "views/purchase_order_views.xml",
        "views/res_config_settings_views.xml",
        "security/ir.model.access.csv"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    'maintainers': ['leonix']
}

