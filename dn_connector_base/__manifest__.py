# -*- coding: utf-8 -*-
{
    "name": "Universal REST Connector Base & Inbound Gateway",
    "version": "19.0.2.0.1",
    "category": "Tools",
    "summary": "Universal REST Connector & Inbound Webhook API Gateway for Odoo 19",
    "description": """
Universal REST Connector & Inbound API Gateway
==============================================
A high-throughput, fault-tolerant Inbound Gateway and Outbound REST integration
engine for Odoo 19.

Features:
- Fast Inbound HTTP Receiver (/connector/in/<token>) with HMAC-SHA256/1/512, Bearer, Basic Auth.
- Transactional Inbox pattern with sequential FIFO ordering and idempotency deduplication.
- Dual execution modes: immediate synchronous vs. deferred asynchronous batch queue.
- Concurrency-safe cron processor using PostgreSQL SELECT FOR UPDATE SKIP LOCKED.
- Pluggable handlers: Store-only, Raw Dynamic Staging Models, Server Actions, Python safe_eval with _dynamic_import.
- Centralized message retention and dead-letter queue operations.
""",
    "author": "MJB Solutions",
    "website": "https://www.mjbsolutions.com",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule_data.xml",
        "data/connector_framework_presets.xml",
        "data/ir_cron_data.xml",
        "views/connector_framework_views.xml",
        "views/connector_inbound_endpoint_views.xml",
        "views/connector_inbound_message_views.xml",
        "views/connector_config_views.xml",
        "views/connector_endpoint_views.xml",
        "views/connector_model_signature_views.xml",
        "views/connector_model_mapping_views.xml",
        "views/connector_code_execution_log_views.xml",
        "views/connector_sync_log_views.xml",
        "views/connector_missing_log_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
