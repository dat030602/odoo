{
    'name': 'Attachment Reminder',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Dynamic attachment reminder system with configurable keywords and activities',
    'description': """
Attachment Reminder for Odoo 19
==============================

This module provides a dynamic and configurable system to remind users to attach files 
when they mention attachments in their email or chatter messages but haven't actually uploaded any files.

Features:
* Dynamic keyword configuration per language and model
* Activity-based reminders with customizable activity types
* Support for regular expressions in keyword matching
* Multi-language support with language-specific configurations
* Model-specific or generic configurations
* Statistics tracking for configuration effectiveness
* Server-side checking for reliable detection
* Technical menu for easy configuration management
* Automatic activity completion when attachments are added
* Data-driven activity templates for easy customization

Usage:
1. Go to Settings > Attachment Reminder > Configurations
2. Create configurations for different languages and models
3. Add keywords (plain text or regex patterns) for each configuration
4. Configure activity types for reminders using data templates
5. When users send messages with matching keywords but no attachments, activities are created automatically
6. Activities are automatically completed when attachments are added to the record

This feature helps prevent forgotten attachments and improves communication efficiency 
through a flexible, configurable system.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'data': [
        'data/attachment_reminder_data.xml',
        'security/ir.model.access.csv',
        'views/attachment_reminder_config_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
