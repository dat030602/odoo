{
    "name": "Bizapps - Summary of import and export of warehouse by cost collection object",
    "summary": "",
    "version": "16.0.0.1",
    'website': "https://bizapps.vn/ung-dung",
    'author': "support@bizapps.vn",
    'company': 'Bizapps',
    "category": "",
    "license": "OPL-1",
    "application": False,
    "installable": True,
    "depends": ["base","purchase","account","biz_ccv_purchase","product"],
    "data": [
        "security/ir.model.access.csv",

        "report/report_view.xml",

        "views/product.xml",
        "wizard/warehouse_summary_by_cost_wizard.xml",
    ],
}
