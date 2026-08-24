# -*- coding: utf-8 -*-
from odoo import models, fields


class MetaBlueprintAction(models.Model):
    """Server action definition within a blueprint."""
    _name = 'meta.blueprint.action'
    _description = 'Blueprint Server Action'

    blueprint_id = fields.Many2one('meta.blueprint', ondelete='cascade')
    xmlid = fields.Char('XML ID', required=True)
    name = fields.Char('Action Name', required=True)
    model_name = fields.Char('Owning Model', required=True)
    binding_model_name = fields.Char('Binding Model')
    state = fields.Selection([('code', 'Code')], default='code')
    code = fields.Text('Python Code')
