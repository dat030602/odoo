# -*- coding: utf-8 -*-
{
    'name': 'DN Payment Connector Base',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': 'Configuration-driven API integration framework for Odoo',
    'description': """
        Generic Integration Framework for Odoo
        ========================================
        A configuration-driven framework for integrating with external systems
        (Payment Gateways, Shipping, ERP, AI, etc.) without modifying core framework.
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
        
        # Menu
        'views/connector_menu.xml',
        
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
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
