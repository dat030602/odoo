{
    "name": "Bizapps - Import inventory value by excel file",
    "summary": "",
    "version": "16.0.0.1",
    "website": "https://bizapps.vn/ung-dung",
    "author": "support@bizapps.vn",
    "company": "Bizapps",
    "category": "Inventory",
    "license": "OPL-1",
    "application": False,
    "installable": True,
    "depends": ["base", "stock", "stock_account"],
    "data": [
        'wizard/stock_inventory_adjustment_name_view.xml',

        'views/stock_valuation_layer.xml',
        'views/stock_quant.xml',
    ],
}
