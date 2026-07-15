# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "CCV: Định mức",
    "version": "1.3",
    "category": "",
    "description": """Định mức""",
    "depends": [
        "ccv_custom_field",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/approvals_category.xml",
        "views/approval_product_line.xml",
        "views/approval_request.xml",
        "views/approval_bom_product.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
