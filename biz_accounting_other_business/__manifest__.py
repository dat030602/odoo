{
    # Required
    "name": "BizApps - Other business accounting documents",

    # Information
    "category": "",
    "version": "16.0.0.1",
    "auto_install": False,
    "installable": True,
    "author": "support@bizapps.vn",
    "website": "https://bizapps.vn/ung-dung",
    "license": "OPL-1",

    "depends": ["base", "account"],
    "data": [
        'reports/rp_accounting_other_business.xml',
        'reports/report_action.xml',

        'views/account_move_view.xml'
    ],
}