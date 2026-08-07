{
    "name": "Universal REST Connector Base",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Universal REST Connector Framework for Odoo - Raw Data First, Business Later",
    "description": """
Universal REST Connector Framework
==================================
A framework to connect to any REST API, auto-discover schema from JSON responses,
create dynamic models/fields/views, and import raw data. Business logic is handled
by separate connector packs (Shopify, WooCommerce, etc.).

Philosophy: Raw Data First - Business Later
""",
    "author": "MJB Solutions",
    "website": "https://www.mjbsolutions.com",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "views/connector_config_views.xml",
        "views/connector_endpoint_views.xml",
        "views/connector_model_signature_views.xml",
        "views/connector_model_mapping_views.xml",
        "views/connector_code_execution_log_views.xml",
        "views/connector_sync_log_views.xml",
        "views/connector_missing_log_views.xml",
        "data/ir_cron_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
