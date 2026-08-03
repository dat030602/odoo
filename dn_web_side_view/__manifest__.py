{
     'name': 'Advanced Dynamic Approval',
     'summary': 'Dynamic approval workflow builder with visual stage hierarchy and Python conditional routing',
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
     'author': 'Dat Nguyen',
     'website': 'https://www.datnguyen.dev',
     'category': 'Tools',
     'version': '19.0.1.0.0',
     'license': 'OPL-1',
     'depends': [
         'base',
         'approvals',
         'web_hierarchy',
     ],
     'data': [
         'security/ir.model.access.csv',
         'views/workflow_config_views.xml',
         'views/workflow_stage_views.xml',
         'views/approval_history_views.xml',
         'wizards/approval_reason_wizard_views.xml',
     ],
     'images': [
         'static/description/screenshot_workflow.png',
         'static/description/screenshot_workflow_stages.png',
         'static/description/screenshot_workflow_stages_form.png',
         'static/description/screenshot_approval_form.png',
         'static/description/screenshot_approval_action_model.png',
     ],
     'assets': {},
     'demo': [],
     'installable': True,
     'application': False,
     'auto_install': False,
     'price': 15.00,
     'currency': 'EUR',
}
