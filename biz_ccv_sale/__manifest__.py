{
    'name': 'Bizapps - Sale',
    'version': '1.6',
    'category': 'Sales/Sales',
    'description': "",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    'depends': ['base', 'sale', 'base_geolocalize', 'sale_management', 'crm', 'purchase', 'stock', 'product', 'sign',
                'report_py3o', 'sale_project', 'sale_renting', 'biz_hide_menu', 'sale_invoice_product_image_app', 'mrp',
                'biz_sign_sequence', 'biz_ccv_account', 'biz_field_image_preview', 'sale_enterprise', 'hr_expense', 'inven_barcode_app', 'to_stock_picking_validate_manual_time', 'biz_ccv_purchase'],
    'data': [
        'data/sequence.xml',

        # Security
        "security/sales_team_security.xml",
        "security/ir.model.access.csv",
        # Report
        "report/ccv_warehouse_transfer_note.xml",
        "report/sale_order_reports.xml",
        "report/sale_report_views.xml",
        "report/purchase_report_views.xml",
        'report/rp_ccv_warehouse_receipt_template.xml',
        'report/rp_ccv_inventory_receipt_template.xml',
        'report/rp_ccv_inventory_export_template.xml',
        "report/report_action.xml",
        "report/ir_actions_report_templates.xml",
        # Wizard
        "wizard/sign_send_request_views.xml",
        # Views
        "views/hr_expense.xml",
        "views/coordinate_tolerancing.xml",
        'views/sale_route_view.xml',
        "views/res_partner_views.xml",
        "views/coordinate_checkin_history.xml",
        "views/crm_lead_views.xml",
        "views/contact_view.xml",
        "views/sale_views.xml",
        "views/crm_team_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_view.xml",
        "views/stock_views.xml",
        "views/product_views.xml",
        "views/sign_request_views.xml",
        "views/res_company_views.xml",
        "views/sign_request_templates.xml",
        'views/sale_route_group_view.xml',
        'views/sale_route_report_view.xml',
        "views/sale_order_type_views.xml",
        "views/purchase_order_type_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_view.xml",
        'views/sale_menus.xml',
        'views/mrp_view.xml',
        'views/sales_audit_dashboard_views.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            # CSS and SCSS
            "biz_ccv_sale/static/src/css/*.css",
            "biz_ccv_sale/static/src/scss/*.scss",
            # XML
            "biz_ccv_sale/static/src/xml/*.xml",
            "biz_ccv_sale/static/src/views/**/*",
            # LIB
            "biz_ccv_sale/static/src/lib/webcam.js",
            # JS
            'biz_ccv_sale/static/src/js/*.js',
        ],
    },
    "external_dependencies": {
        'python': ['beautifulsoup4']
    }
}
