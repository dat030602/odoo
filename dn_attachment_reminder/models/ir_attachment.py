# -*- coding: utf-8 -*-
from odoo import models, api


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically complete attachment reminder activities"""
        attachments = super().create(vals_list)
        
        # Skip if context says to skip attachment reminder auto-complete
        if self.env.context.get('skip_attachment_reminder_auto_complete'):
            return attachments
        
        # Check each attachment for related reminder activities to complete
        for attachment in attachments:
            if attachment.res_model and attachment.res_id:
                attachment._complete_attachment_reminder_activities()
        
        return attachments
    
    def _complete_attachment_reminder_activities(self):
        """Complete attachment reminder activities for this attachment's record
        
        This method finds any pending attachment reminder activities related to
        the same record and automatically marks them as done when an attachment
        is added.
        """
        if not self.res_model or not self.res_id:
            return
        
        try:
            # Find pending attachment reminder activities for this record
            activities = self.env['mail.activity'].search([
                ('res_model', '=', self.res_model),
                ('res_id', '=', self.res_id),
                ('is_attachment_reminder', '=', True),
                ('state', '!=', 'done'),
            ])
            
            if activities:
                # Automatically complete the activities
                for activity in activities:
                    try:
                        activity.action_done()
                    except Exception:
                        # Log error but don't prevent attachment creation
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error('Error completing attachment reminder activity %s', activity.id)
        except Exception as e:
            # Log error but don't prevent attachment creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error('Error completing attachment reminder activities: %s', str(e))
            