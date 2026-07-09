import re
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _get_matching_config(self):
        """Get matching attachment reminder configuration for this message

        Returns:
            attachment.reminder.config record or None
        """
        self.ensure_one()
        # Access fields from parent model (mail.message)
        # These fields exist in the base model: model, res_id, message_type
        model_name = self.model if hasattr(self, 'model') else None
        res_id = self.res_id if hasattr(self, 'res_id') else None
        message_type = self.message_type if hasattr(self, 'message_type') else None

        if not model_name or not res_id:
            return None

        # Get user's language
        language_code = self.env.user.lang or 'en_US'

        # Get matching configuration using the environment
        Config = self.env['attachment.reminder.config']

        # Call the method - this will exist at runtime when the model is loaded
        try:
            config = Config.get_matching_config(
                model_name=model_name,
                language_code=language_code,
                message_type=message_type
            )
        except AttributeError:
            # Fallback if method doesn't exist (shouldn't happen in normal operation)
            config = None
        return config

    def _check_attachment_keywords(self, body_text, config):
        """Check if the message text contains attachment-related keywords from config

        Args:
            body_text (str): The message text to check
            config (attachment.reminder.config): Configuration to use for checking

        Returns:
            bool: True if attachment keywords are found
        """
        if not body_text or not config:
            return False

        # Convert to plain text if it's HTML
        if '<' in body_text and '>' in body_text:
            body_text = html2plaintext(body_text)

        # Check each keyword in the configuration
        return any(keyword.match(body_text) for keyword in config.keyword_ids)

    def _has_attachments(self):
        """Check if the message has any attachments

        Returns:
            bool: True if there are attachments
        """
        return bool(self.attachment_ids and len(self.attachment_ids) > 0)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to check for forgotten attachments"""
        messages = super().create(vals_list)

        # Skip if context says to skip attachment reminder
        if self.env.context.get('skip_attachment_reminder'):
            return messages
        # Check each message for forgotten attachments
        for message in messages:
            if message.message_type in ['email', 'comment', 'user_notification']:
                config = message._get_matching_config()
                if config:
                    body_text = message.body
                    if (message._check_attachment_keywords(body_text, config) and not message._has_attachments()):
                        message._create_attachment_reminder_activity(config)
        return messages

    def _create_attachment_reminder_activity(self, config):
        """Create an activity to remind the user about forgotten attachments

        Args:
            config (attachment.reminder.config): Configuration to use for activity creation
        """
        # Get the related record
        if not self.res_id or not self.model:
            return

        try:
            # Find the related record
            record = self.env[self.model].browse(self.res_id)
            if not record.exists():
                return

            # Check if the model supports activities
            if not hasattr(record, 'activity_ids'):
                return

            # Get or create the attachment reminder activity type
            activity_type = self._get_attachment_reminder_activity_type(config)
            if not activity_type:
                return

            # Create the activity for the message author
            if self.author_id and self.author_id.user_ids:
                user = self.author_id.user_ids[0]
                
                # Use activity summary and note from activity type template
                summary = activity_type.summary or _('Missing Attachment?')
                note = activity_type.default_note or _(
                    'It seems you may have forgotten to attach a file to this message. '
                    'The content mentions attachments but no files were uploaded.'
                )

                # Create activity directly with custom fields
                activity_vals = {
                    'res_model_id': self.env['ir.model']._get(self.model).id,
                    'res_id': self.res_id,
                    'activity_type_id': activity_type.id,
                    'user_id': user.id,
                    'summary': summary,
                    'note': note,
                    'date_deadline': fields.Date.today(),
                    'related_message_id': self.id,
                    'is_attachment_reminder': True,
                    'attachment_reminder_config_id': config.id,
                }
                self.env['mail.activity'].create(activity_vals)
                config.increment_match_count()
        except Exception as e:
            # Log error but don't prevent message creation
            logger.error('Error creating attachment reminder activity: %s', str(e))

    def _get_attachment_reminder_activity_type(self, config):
        """Get the attachment reminder activity type from config
        
        Args:
            config (attachment.reminder.config): Configuration to use
            
        Returns:
            mail.activity.type record or None
        """
        # Use config's activity type if specified
        if config.activity_type_id:
            return config.activity_type_id
        
        # Fallback to generic activity type if config allows
        if config.create_default_activity:
            try:
                # Try to find existing default activity type
                activity_type = self.env['mail.activity.type'].search([
                    ('name', '=', _('Attachment Reminder')),
                    ('res_model', '=', False)
                ], limit=1)
                if activity_type:
                    return activity_type
            except Exception:
                pass
        
        return None
