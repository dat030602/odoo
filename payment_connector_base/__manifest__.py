# -*- coding: utf-8 -*-
{
    'name': 'Generic Integration Framework for Odoo',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': 'Configuration-driven API integration framework for Odoo',
    'description': """
        Generic Integration Framework for Odoo
        ========================================
        
        A configuration-driven (low-code) framework for integrating with any external system
        without modifying the core framework.
        
        Supported integrations:
        - Payment Gateways (MoMo, VNPay, Stripe, etc.)
        - Shipping Providers (GHN, GHTK, DHL, etc.)
        - ERP/CRM Systems
        - E-Invoice Providers
        - SMS/Email Services
        - Banking Services
        - AI Services
        - OAuth Providers
        
        Features:
        - Dynamic configuration through Odoo UI
        - Multiple authentication methods (API Key, Basic, Bearer, JWT, OAuth2, HMAC, Custom)
        - Multiple hash algorithms (MD5, SHA1, SHA256, SHA512, HMAC SHA256, HMAC SHA512, Custom)
        - Flexible payload mapping with compute pipeline
        - Request/Response transformation
        - Webhook handling
        - Scheduled synchronization
        - Comprehensive logging and audit trail
        - Multi-provider support
        - Multi-environment support (Sandbox, Production, UAT)
        - Multi-company support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        # Security
        'security/connector_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/connector_data.xml',
        
        # Views
        'views/provider_views.xml',
        'views/environment_views.xml',
        'views/setting_views.xml',
        'views/api_views.xml',
        'views/endpoint_views.xml',
        'views/mapping_views.xml',
        'views/compute_views.xml',
        'views/auth_views.xml',
        'views/hash_views.xml',
        'views/execution_views.xml',
        'views/log_views.xml',
        
        # Menu
        'views/connector_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'payment_connector_base/static/src/js/connector.js',
            'payment_connector_base/static/src/css/connector.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
