# -*- coding: utf-8 -*-
from odoo import models, fields


class MetaBlueprintView(models.Model):
    """View definition within a blueprint."""
    _name = 'meta.blueprint.view'
    _description = 'Blueprint View'

    blueprint_id = fields.Many2one('meta.blueprint', ondelete='cascade')
    xmlid = fields.Char('XML ID', required=True)
    name = fields.Char('View Name', required=True)
    model_name = fields.Char('Model')
    arch_resolve = fields.Char('Arch Resolve (Dict String)')
    arch = fields.Text('XML Arch', required=True)
