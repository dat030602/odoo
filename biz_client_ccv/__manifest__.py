{
    # Required
    "name": "BizApps - Client CCV",

    # Information
    "category": "",
    "version": "16.0.0.3",
    "application": True,
    "auto_install": False,
    "installable": True,
    "summary": "Client CVV",
    "description": "Client CCV",
    "author": "support@bizapps.vn",
    "maintainer": "support@bizapps.vn",
    "contributors": ["support@bizapps.vn"],
    "website": "https://bizapps.vn/ung-dung",
    "sequence": 100,
    "license": "OPL-1",
    "pre_init_hook": "",
    "post_init_hook": "",
    "uninstall_hook": "",

    # Available packages
    "depends": ["base", "mrp", "sale_stock", "stock", "account", "account_accountant", "account_followup",  "sale_timesheet", "sale_renting","account_reports"],
    "data": [
        'data/ir_cron.xml',
        # Security
        "security/ir.model.access.csv",
        "security/mrp_production_security.xml",
        # Report
        "report/mrp_production_templates.xml",
        # Views
        "views/mrp_production_views.xml",
        "views/res_users_views.xml",
        'views/sale_order_view.xml',
        'views/account_view.xml',
        'views/res_partner_views.xml',
        'views/account_payment_views.xml',
        'views/res_currency_views.xml',

        'wizard/create_invoice_wizard.xml'

    ],
    'assets': {
       'web.assets_backend': [
           'biz_client_ccv/static/src/js/tree_button.js',
           'biz_client_ccv/static/src/xml/tree_button.xml',
       ],
    },
}