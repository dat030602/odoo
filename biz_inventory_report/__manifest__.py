{
    "name": "Bizapps - Inventory Report",
    "summary": "",
    "version": "16.0.0.1",
    "website": "https://bizapps.vn/ung-dung",
    "author": "support@bizapps.vn",
    "company": "Bizapps",
    "category": "Inventory",
    "license": "OPL-1",
    "application": False,
    "installable": True,
    "depends": ["base", "stock", "ccv_sql"],
    "data": [
      "reports/inventory_report_pdf_template.xml",
      "reports/report_action.xml",
      
      "views/stock_quant_views.xml",
    ],
}
