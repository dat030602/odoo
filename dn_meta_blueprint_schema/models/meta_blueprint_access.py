# -*- coding: utf-8 -*-
from odoo import models, fields


class MetaBlueprintAccess(models.Model):
    """Access rights definition within a blueprint."""
    _name = 'meta.blueprint.access'
    _description = 'Blueprint Access Rights'

    blueprint_id = fields.Many2one('meta.blueprint', ondelete='cascade')
    name = fields.Char('Rule Name', required=True)
    model_name = fields.Char('Model')
    group_xmlid = fields.Char('Group XML ID')
    perm_read = fields.Boolean('Read', default=True)
    perm_write = fields.Boolean('Write', default=True)
    perm_create = fields.Boolean('Create', default=True)
    perm_unlink = fields.Boolean('Delete')
