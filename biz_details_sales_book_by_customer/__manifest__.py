{
    "name": "Bizapps - Details Sales Book By Customer",
    "summary": "",
    "version": "16.0.0.1",
    'website': "https://bizapps.vn/ung-dung",
    'author': "support@bizapps.vn",
    'company': 'Bizapps',
    "category": "",
    "license": "OPL-1",
    "application": False,
    "installable": True,
    "depends": [
        "base","account","account_accountant","sale","sale_management", "sale_stock","report_xlsx", "l10n_vn",
        "account_reports", "biz_ccv_sale", "biz_ccv_purchase","biz_conveyor_picking",
        "ccv_custom_field"],
    "data": [
        "data/parameter.xml",
        "security/ir.model.access.csv",
        "report/report_action.xml",
        "report/details_sales_book_by_customer_template.xml",
        "wizards/wz_select_time_view.xml",
        "views/details_sales_book_by_customer_line.xml",
        "views/details_sales_book_by_customer.xml",
        
        'views/stock_picking_views.xml',
    ],
}
