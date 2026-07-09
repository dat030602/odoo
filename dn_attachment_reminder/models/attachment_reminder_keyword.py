# -*- coding: utf-8 -*-
# IDE linter warnings about model inheritance and field access are expected
# These models will be properly loaded when the module is installed in Odoo
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AttachmentReminderKeyword(models.Model):
    _name = 'attachment.reminder.keyword'
    _description = 'Attachment Reminder Keyword'
    _order = 'sequence, name'

    name = fields.Char('Keyword', required=True, help='The keyword to search for in message content')
    sequence = fields.Integer('Sequence', default=10)
    config_id = fields.Many2one('attachment.reminder.config', string='Configuration', required=True, ondelete='cascade')
    case_sensitive = fields.Boolean('Case Sensitive', default=False, help='If checked, keyword matching will be case-sensitive')
    is_regex = fields.Boolean('Regular Expression', default=False, help='If checked, the keyword will be treated as a regular expression pattern')
    
    @api.constrains('is_regex', 'name')
    def _check_regex_pattern(self):
        """Validate regex patterns"""
        for keyword in self:
            if keyword.is_regex:
                import re
                try:
                    re.compile(keyword.name)
                except re.error as e:
                    raise ValidationError(_('Invalid regular expression: %s') % str(e))
    
    def match(self, text):
        """Check if this keyword matches the given text
        
        Args:
            text (str): Text to search in
            
        Returns:
            bool: True if keyword matches
        """
        if not text or not self.name:
            return False
        
        if self.is_regex:
            import re
            flags = 0 if self.case_sensitive else re.IGNORECASE
            return re.search(self.name, text, flags) is not None
        else:
            if self.case_sensitive:
                return self.name in text
            else:
                return self.name.lower() in text.lower()
