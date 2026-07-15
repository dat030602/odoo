{
    "name": "Bizapps - Purchase Invoices List CCV",
    "summary": "",
    "version": "16.0.0.1",
    'website': "https://bizapps.vn/ung-dung",
    'author': "support@bizapps.vn",
    'company': 'Bizapps',
    "category": "",
    "license": "OPL-1",
    "application": False,
    "installable": True,
    "depends": ["base","account","account_accountant","sale","sale_management","purchase","report_xlsx", "l10n_vn", "account_reports", "biz_viettel_sinvoice_v2"],
    "data": [
        "security/ir.model.access.csv",
        
        "views/product_template_view.xml",
        "views/account_account_view.xml",
        "views/account_move_view.xml",
        "views/bank_rec_widget_views.xml",
        "views/res_config_settings_view.xml",
        "views/purchase_receipt_sheet_line_view.xml",
        "views/purchase_receipt_sheet_view.xml",

        "report/report_view.xml",

        "wizards/purchase_receipt_sheet_wizard.xml",
        "views/menu.xml",
    ],
    'qweb': [
        "static/src/xml/account_reconciliation.xml",
    ],
}
