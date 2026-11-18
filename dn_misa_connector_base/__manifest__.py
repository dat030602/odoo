{
    'name': 'MISA Connector Base',
    'version': '19.0.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Core connectivity, authentication, organization mapping, rate limiting, and queue management for MISA integration',
    'description': """
MISA Connector Base
===================

This module serves as the foundational infrastructure for integrating Odoo with MISA platforms:
- Dual Authentication management for MISA meInvoice (e-Invoicing) and MISA INBOT (Input/Output Invoices).
- Token lifecycle management, caching, 2FA support, and automatic re-authentication upon token expiration.
- Multi-company connection settings with test connection utilities.
- Organization and branch synchronization from MISA INBOT (Subscriber & Organization structure).
- Subscription pack and resource quota monitoring (NumberOfInvoice, NumberInvUsed, NumberInvStill).
- Centralized API request/response logging (misa.api.log) with credential masking and execution duration tracking.
- Sequential queue dispatcher (misa.queue.job) with series row locking (with_for_update), rate limiting control (10 req/60s), batching (max 30 records, 400 lines), and automated retries.
    """,
    'author': 'Dyan',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/misa_organization_views.xml',
        'views/misa_api_log_views.xml',
        'views/misa_queue_job_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
