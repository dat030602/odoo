# -*- coding: utf-8 -*-
{
    # Display name shown in Odoo Apps / Apps Menu
    'name': 'Advanced Dynamic Approval',
    # Short summary of features (1 sentence, shown in app search list)
    'summary': 'Dynamic approval workflow builder with visual stage hierarchy and Python conditional routing',
    # Detailed description (can be omitted if static/description/index.html exists)
    'description': """
Advanced approval workflow engine for Odoo 19 that extends the existing Approval module 
while completely replacing the default approval execution flow.

Features:
- Visual workflow builder using hierarchy view
- Multi-stage approval process
- Python-based conditional routing (if/else)
- Dynamic form and list view generation
- One approval category = one generated approval interface
- Automatic menu and action generation
- Dynamic field behavior based on current approval stage
    """,
    # Author and website (required by App Store)
    'author': 'Dat Nguyen',
    'website': 'https://www.datnguyen.dev',
    # Module category on Odoo Store (Tools / Miscellaneous recommended for utility modules)
    'category': 'Tools',
    # Version format: [Odoo version].[module version] (19.0 -> Odoo 19)
    'version': '19.0.1.0.0',
    # License (MUST be OPL-1 for paid apps; LGPL-3/GPL-3 only for free open-source apps)
    'license': 'OPL-1',
    # Dependencies (modules this module requires)
    'depends': [
        'base',
        'approvals',
        'web_hierarchy',
    ],
    # Data files loaded at install/upgrade: Security -> Data -> Views -> Reports -> Wizards
    'data': [
        # 1. Security / Access Rights
        'security/ir.model.access.csv',
        # 2. Views
        'views/workflow_config_views.xml',
        'views/workflow_stage_views.xml',
        'views/approval_history_views.xml',
        # 3. Wizards
        'wizards/approval_reason_wizard_views.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    # Static assets (JS, CSS, SCSS, QWeb templates)
    'assets': {
    },
    # Demo data (only loaded in demonstration mode)
    'demo': [],
    # Installation configuration
    'installable': True,           # Whether the module can be installed
    'application': False,          # False: treated as a utility module, not a standalone app
    'auto_install': False,         # True: auto-installs when all dependencies are installed
    # Pricing (for paid apps on Odoo Store — MUST use OPL-1 license)
    'price': 100.00,
    'currency': 'EUR',
}
