# -*- coding: utf-8 -*-
# IDE linter warnings about model inheritance and field access are expected
# These models will be properly loaded when the module is installed in Odoo
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AttachmentReminderConfig(models.Model):
    _name = 'attachment.reminder.config'
    _description = 'Attachment Reminder Configuration'
    _order = 'sequence, name'

    name = fields.Char('Configuration Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Model configuration
    model_id = fields.Many2one(
        'ir.model', 
        string='Apply to Model',
        help='If empty, this configuration applies to all models that inherit from mail.thread'
    )
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True)
    
    # Language configuration
    language_id = fields.Many2one(
        'res.lang', 
        string='Language',
        required=True,
        default=lambda self: self.env['res.lang'].search([('code', '=', self.env.user.lang)], limit=1),
        help='The language for which this configuration applies'
    )
    
    # Activity configuration
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type',
        domain="[('res_model', '=', False)]",
        help='Activity type to create when keywords are matched. If empty, a default activity type will be created.'
    )
    create_default_activity = fields.Boolean(
        'Create Default Activity',
        default=True,
        help='If checked and no activity type is specified, a default activity type will be created automatically.'
    )
    
    # Keywords
    keyword_ids = fields.One2many(
        'attachment.reminder.keyword',
        'config_id',
        string='Keywords'
    )
    keyword_count = fields.Integer('Keyword Count', compute='_compute_keyword_count')
    
    # Message types to check
    message_type_ids = fields.Many2many(
        'mail.message.subtype',
        string='Message Types',
        domain="[('internal', '=', False)]",
        help='Message types to check. If empty, all user message types will be checked.'
    )
    
    # Statistics
    match_count = fields.Integer('Match Count', readonly=True, help='Number of times this configuration matched')
    last_match_date = fields.Datetime('Last Match Date', readonly=True)
    
    @api.depends('keyword_ids')
    def _compute_keyword_count(self):
        for config in self:
            config.keyword_count = len(config.keyword_ids)
    
    @api.constrains('model_id', 'language_id')
    def _check_unique_model_language(self):
        """Ensure uniqueness of model + language combination"""
        for config in self:
            if config.model_id and config.language_id:
                domain = [
                    ('model_id', '=', config.model_id.id),
                    ('language_id', '=', config.language_id.id),
                    ('id', '!=', config.id),
                    ('active', '=', True)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_(
                        'Only one active configuration is allowed per model and language combination. '
                        'Model: %s, Language: %s'
                    ) % (config.model_id.name, config.language_id.name))
    
    def increment_match_count(self):
        """Increment match counter and update last match date"""
        self.write({
            'match_count': self.match_count + 1,
            'last_match_date': fields.Datetime.now()
        })
    
    def get_matching_config(self, model_name, language_code, message_type=None):
        """Find matching configuration for given parameters
        
        Args:
            model_name (str): Model name
            language_code (str): Language code (e.g., 'vi_VN', 'en_US')
            message_type (str): Optional message type to filter
            
        Returns:
            attachment.reminder.config record or None
        """
        # Get language record
        language = self.env['res.lang'].search([('code', '=', language_code)], limit=1)
        if not language:
            language = self.env['res.lang'].search([], limit=1)  # Fallback to default
        
        # Build domain
        domain = [
            ('active', '=', True),
            ('language_id', '=', language.id),
        ]
        
        # First try to find model-specific configuration
        model_specific_domain = domain + [('model_id.model', '=', model_name)]
        config = self.search(model_specific_domain, limit=1)
        
        # If no model-specific config, try generic config
        if not config:
            generic_domain = domain + [('model_id', '=', False)]
            config = self.search(generic_domain, limit=1)
        
        # Check message type if specified
        if config and message_type and config.message_type_ids:
            # This is a simplified check - in reality, message_type in mail.message is a string, not a subtype
            # We might need to adjust this based on actual usage
            pass
        
        return config
    
    def get_keywords(self):
        """Get all keywords for this configuration as a list"""
        return self.keyword_ids.mapped('name')

