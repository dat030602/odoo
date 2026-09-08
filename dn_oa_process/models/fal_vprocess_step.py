# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError

class fal_vprocess_step(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    _name = "fal.vprocess.step"
    _description = "Step"
    _order = "process_id,sequence,id"

    name = fields.Char("Name", default="Step", tracking=True)
    active = fields.Boolean("Active", default=True, tracking=True)

    auto_confirm_no_conditions = fields.Boolean("Auto confirm if no conditions", default=False, tracking=True)
    allow_anyone_no_conditions = fields.Boolean("Allow anyone if no conditions", default=True, tracking=True)
    auto_confirm_no_active_rules = fields.Boolean("Auto confirm if no active rules", default=False, tracking=True)
    
    disable_edit = fields.Boolean("Disable Edition", default=True, tracking=True)
    disable_actions = fields.Boolean("Disable Actions", default=True, tracking=True)
    allowed_actions_list = fields.Char("Allowed actions names", default="", tracking=True)
    
    enable_email = fields.Boolean("Send email to authorized users", default=False, tracking=True)
    enable_activity = fields.Boolean("Set activity to authorized users", default=False, tracking=True)
    #activity_text = fields.Char("Activity text", default="Please review $MODEL")
    
    #activity_type_id = fields.Many2one('mail.activity.type', 'Activity Type', required=False)
    #email_template_id = fields.Many2one('mail.template', 'Email Template', required=False)
    
    buttons_back = fields.Boolean("Allow back button", default=True, tracking=True)
    buttons_reset = fields.Boolean("Allow reset button", default=True, tracking=True)
    
    back_to_step_id = fields.Many2one(
        'fal.vprocess.step', 
        'Back To Step', 
        tracking=True,
        help="Specify which step the Back button should go to. If not set, defaults to the previous step in sequence."
    )

    @api.onchange('buttons_back')
    def _onchange_buttons_back(self):
        for record in self:
            if not record.buttons_back:
                record.back_to_step_id = False

    sequence = fields.Integer("Sequence", default=0, tracking=True)
    process_id = fields.Many2one('fal.vprocess', 'Process', tracking=True)
    
    rule_ids = fields.One2many("fal.vprocess.rule", 'step_id', 'Rules', ondelete='cascade')
    
    action_string_confirm = fields.Char("Action on confirm", default="", tracking=True)
    action_string_cancel = fields.Char("Action on cancel", default="", tracking=True)
    action_string_back = fields.Char("Action on back", default="", tracking=True)
    action_string_reset = fields.Char("Action on reset", default="", tracking=True)
    
    field_string_confirm = fields.Char("Change field on confirm", default="", tracking=True)
    field_string_cancel = fields.Char("Change field on cancel", default="", tracking=True)
    field_string_back = fields.Char("Change field on back", default="", tracking=True)
    field_string_reset = fields.Char("Change field on reset", default="", tracking=True)

    def _valid_field_parameter(self, field, name):
        return name == 'ondelete' or super()._valid_field_parameter(field, name)
