# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    # Add a field to track if this is an attachment reminder activity
    is_attachment_reminder = fields.Boolean(
        string='Is Attachment Reminder',
        help='Indicates if this activity was created automatically to remind about forgotten attachments'
    )
    
    # Link to the related message
    related_message_id = fields.Many2one(
        'mail.message',
        string='Related Message',
        help='The message that triggered this attachment reminder'
    )
    
    # Link to the configuration that created this activity
    # type: ignore is added because the model is defined in the same module
    attachment_reminder_config_id = fields.Many2one(
        'attachment.reminder.config',  # type: ignore
        string='Reminder Configuration',
        help='The configuration that was used to create this reminder activity'
    )
    
    def action_done(self):
        """Override action_done to handle attachment reminder completion"""
        res = super().action_done()
        # Additional logic for attachment reminder activities can be added here
        return res
