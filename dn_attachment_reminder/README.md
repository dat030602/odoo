# Attachment Reminder Module for Odoo 19

## Overview

This module provides a dynamic and configurable system to remind users to attach files when they mention attachments in their email or chatter messages but haven't actually uploaded any files. The module uses server-side checking and creates activities to remind users about forgotten attachments.

## Features

- **Dynamic Configuration**: Configure keywords and activities per language and model
- **Multi-language Support**: Language-specific configurations with translated keywords
- **Model-Specific Rules**: Create configurations for specific models or generic rules for all models
- **Activity-Based Reminders**: Creates automatic activities when users forget to attach files
- **Regular Expression Support**: Advanced keyword matching with regex patterns
- **Statistics Tracking**: Monitor configuration effectiveness with match counters
- **Server-Side Processing**: Reliable checking on the server side for consistent behavior
- **Technical Menu**: Easy configuration management in Settings menu
- **Smart Detection**: Only checks user messages, not system notifications

## Installation

1. Copy the `dn_attachment_reminder` folder to your Odoo `addons` directory
2. Update your Odoo apps list
3. Install the module from the Apps menu
4. Access configuration via Settings > Attachment Reminder (requires System access)

## Configuration

### Access Configuration Menu

Navigate to: **Settings > Attachment Reminder > Configurations**

### Creating Configurations

1. Click "Create" to add a new configuration
2. Fill in the required fields:
   - **Name**: Configuration name (translatable)
   - **Model**: Select specific model or leave empty for generic rules
   - **Language**: Select language for this configuration
   - **Activity Type**: Choose existing activity type or enable auto-creation

### Adding Keywords

1. Open a configuration record
2. Go to the "Keywords" tab
3. Add keywords with the following options:
   - **Keyword**: The word or phrase to search for
   - **Case Sensitive**: Enable for case-sensitive matching
   - **Regular Expression**: Enable for regex pattern matching

### Example Configurations

#### Vietnamese Keywords Configuration
- **Language**: Vietnamese (or English with Vietnamese keywords)
- **Keywords**: "đính kèm", "file", "tệp", "tài liệu", "báo giá", "hóa đơn", "gửi kèm", etc.

#### English Keywords Configuration
- **Language**: English
- **Keywords**: "attach", "attachment", "file", "document", "invoice", "quote", etc.

## Usage

1. When composing an email or chatter message, if you mention attachment-related keywords
2. And you haven't attached any files
3. An activity will be automatically created after sending the message
4. The activity appears in the document's chatter with a paperclip icon
5. You can then:
   - Mark the activity as done if you meant to send without attachments
   - Edit the message to add attachments

## Technical Details

- **Module Name**: dn_attachment_reminder
- **Version**: 19.0.1.0.0
- **Dependencies**: mail
- **License**: LGPL-3

### Implementation

The module consists of several models:

1. **attachment.reminder.config**: Main configuration model
   - Links to models and languages
   - Contains keyword definitions
   - Tracks statistics

2. **attachment.reminder.keyword**: Keyword definitions
   - Supports plain text and regex patterns
   - Case-sensitive options
   - Linked to configurations

3. **mail.message**: Extended to check for forgotten attachments
   - Uses dynamic configuration matching
   - Creates activities based on configuration

4. **mail.activity**: Extended to track reminder activities
   - Links back to original message
   - Links to configuration used

### Files Structure

```
dn_attachment_reminder/
├── __manifest__.py                    # Module manifest
├── README.md                         # This file
├── models/
│   ├── __init__.py                    # Models initialization
│   ├── attachment_reminder_config.py  # Configuration models
│   ├── mail_message.py                # Mail message extension
│   └── mail_activity.py               # Mail activity extension
├── views/
│   └── attachment_reminder_config_views.xml  # UI views
├── security/
│   └── ir.model.access.csv           # Access rights
└── data/
    └── attachment_reminder_data.xml  # Default configurations
```

## Customization

### Adding Custom Keywords via UI

1. Navigate to Settings > Attachment Reminder > Configurations
2. Open the appropriate configuration for your language
3. Go to the Keywords tab
4. Add custom keywords using the interface

### Creating Model-Specific Rules

1. Create a new configuration
2. Select the specific model in the "Apply to Model" field
3. Add keywords specific to that model's context
4. Configure appropriate activity type

### Using Regular Expressions

For advanced pattern matching, enable the "Regular Expression" option on keywords:

```
# Match file extensions with various patterns
\.(pdf|doc|docx|xlsx|xls)$

# Match email attachment phrases
(attached|enclosed|attached is|enclosed is).+(file|document)

# Match common attachment phrases
please find attached|see attached file|attached document
```

### Disabling for Specific Messages

To skip attachment checking for specific messages, use the context:

```python
message.with_context(skip_attachment_reminder=True).message_post(
    body='Your message here'
)
```

## How It Works

1. **Message Creation**: When a message is created, the module checks if it's a user message (email, comment, or user_notification)

2. **Configuration Matching**: Finds the best matching configuration based on:
   - User's language
   - Message model
   - Message type (if configured)

3. **Keyword Detection**: The message body is analyzed for attachment-related keywords from the matched configuration

4. **Attachment Check**: The module verifies if any attachments are linked to the message

5. **Activity Creation**: If keywords are found but no attachments exist, an activity is created based on the configuration

6. **Statistics Update**: Configuration match counters are updated for monitoring

## Benefits

- **Flexible Configuration**: Customize keywords and rules per language and model
- **Professional Interface**: Clean UI for configuration management
- **Non-Intrusive**: Uses the standard activity system rather than blocking message sending
- **Trackable**: Statistics and logging for monitoring effectiveness
- **Scalable**: Server-side processing works consistently across all clients
- **Multi-language**: Proper support for international environments
- **Advanced Matching**: Regex support for complex pattern detection

## Access Rights

- **Regular Users**: Can see reminder activities but cannot modify configurations
- **System Administrators**: Full access to configuration management via Settings menu

## Default Configurations

The module comes with default configurations for:
- **English keywords**: Common attachment-related terms in English
- **Vietnamese keywords**: Common attachment-related terms in Vietnamese (using English language base)

Administrators can modify, extend, or remove these default configurations as needed.

## License

This module is licensed under LGPL-3.

## Support

For issues and questions, please contact your system administrator.
