# ©  2008-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

{
    "name": "Bizapps - Change Unit of measure",
    "summary": "Allows changing the unit of measurement even after a transaction has occurred",
    "version": "16.0.1.0.0",
    "category": "Generic Modules",
    "depends": ["product", "account", "stock", "sale", "purchase"],
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    'company': 'Bizapps',
    'support': 'support@bizapps.vn',
    "license": "OPL-1",
    "data": [
        "security/sale_security.xml",
        "wizard/product_change_uom_view.xml",
        "security/ir.model.access.csv",
    ],
    "images": ["static/description/icon.png"],
}
