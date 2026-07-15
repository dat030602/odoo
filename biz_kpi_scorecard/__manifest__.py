# -*- coding: utf-8 -*-
{
    "name": "BizApps - KPI Balanced Scorecard",
    "version": "16.0.1.0.4",
    "category": "Extra Tools",
    'author': 'support@bizapps.vn',
    'website': 'https://www.bizapps.vn',
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "mail",'hr'
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/cron.xml",
        "wizard/kpi_copy_template.xml",
        "views/kpi_measure_item.xml",
        "views/kpi_measure.xml",
        "views/kpi_constant.xml",
        "views/kpi_item.xml",
        "views/kpi_period.xml",
        "views/kpi_category.xml",
        "views/kpi_scorecard_line.xml",
        "views/res_config_settings.xml",
        "views/menu.xml",
        "data/crm_measures.xml",
        "data/sale_measures.xml",
        "data/invoice_measures.xml",
        "data/project_measures.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "biz_kpi_scorecard/static/src/js/*.js",
            "biz_kpi_scorecard/static/src/css/*.css",
            "biz_kpi_scorecard/static/src/xml/*.xml"
        ],
        # "web.assets_qweb": [
        #     "biz_kpi_scorecard/static/src/xml/*.xml"
        # ]
    },
    "demo": [

    ],
    "external_dependencies": {},
    "summary": "The tool to set up KPI targets and control their fulfillment by periods",
    "description": """
For the full details look at static/description/index.html

* Features * 

- Real-time control and historical trends
- Drag-and-drop formulas for KPIs
- Shared KPIs and self-control
- KPI settings to process Odoo data



#odootools_proprietary

    """,
    "images": [
        "static/description/main.png"
    ],
    "price": "198.0",
    "currency": "EUR",
    "live_test_url": "https://faotools.com/my/tickets/newticket?&url_app_id=138&ticket_version=15.0&url_type_id=3",
}
