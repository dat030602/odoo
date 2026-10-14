{
    'name': "GraphQL API Gateway for Odoo",
    'version': "19.0.1.0.0",
    'category': "Technical/API",
    'author': "Dat Nguyen / Antigravity",
    'license': "LGPL-3",
    'summary': "High-performance GraphQL API Gateway with API Key Auth, Odoo ACL, Atomic Savepoint Rollback, and Security Blocklist",
    'description': """
GraphQL API Gateway for Odoo 19
================================
A production-ready, high-performance GraphQL API Gateway running directly inside Odoo:
- Native Bearer API Key Authentication (scope: 'graphql')
- Strict adherence to Odoo ORM ACL, Record Rules, Multi-company (no sudo bypass)
- Exact quoted model syntax support: `"res.partner"(first: 10)` alongside standard `res__partner`
- Atomic Savepoint Rollback: If any mutation fails, the entire request rolls back cleanly
- Multi-tier Blocklist: Model and field deny rules (Global and per-API Key)
- Anti-Scraping Protection: Depth limit, default limits (20/100), and atomic rate limiting
- File Upload Prohibition: Rejects multipart/form-data uploads immediately
- API Key Expiration & In-place Key Rotation (`rotateApiKey` mutation)
- Independent Audit Logging: Logs committed using isolated cursor even on rollback
    """,
    'depends': ['base', 'web'],
    'external_dependencies': {
        'python': ['graphql'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/default_whitelist.xml',
        'data/default_deny.xml',
        'views/graphql_model_views.xml',
        'views/graphql_key_views.xml',
        'views/graphql_deny_views.xml',
        'views/graphql_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
