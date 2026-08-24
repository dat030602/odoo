# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MetaBlueprintSchema(models.Model):
    """Unified schema table combining Models and Fields.
    Items are processed in exact sequence order during build."""
    _name = 'meta.blueprint.schema'
    _description = 'Blueprint Schema (Model & Fields)'
    _order = 'sequence, id'

    blueprint_id = fields.Many2one('meta.blueprint', ondelete='cascade')
    sequence = fields.Integer(default=10)

    item_type = fields.Selection([
        ('model', 'Model'),
        ('field', 'Field')
    ], string='Type', required=True, default='field')

    # Common fields
    model_name = fields.Char('Target Model (e.g. x_sale)', required=True)
    name = fields.Char('Technical Name (Model/Field)')
    label = fields.Char('Human Label', required=True)

    # Model-specific fields
    is_transient = fields.Boolean('Is Transient (Wizard)')

    # Field-specific fields
    ttype = fields.Selection([
        ('char', 'Char'), ('text', 'Text'), ('integer', 'Integer'),
        ('float', 'Float'), ('monetary', 'Monetary'), ('boolean', 'Boolean'),
        ('date', 'Date'), ('datetime', 'Datetime'), ('many2one', 'Many2one'),
        ('one2many', 'One2many'), ('many2many', 'Many2many')
    ], string='Field Type')

    relation = fields.Char('Relation (Target Model)')
    relation_field = fields.Char('Relation Field (For One2many)')
    related = fields.Char('Related Path')
    store = fields.Boolean('Store', default=True)
    depends = fields.Char('Depends')
    compute = fields.Text('Compute Python Code')

    @api.onchange('item_type')
    def _onchange_item_type(self):
        """Clear field-specific values when switching to Model type."""
        if self.item_type == 'model':
            self.ttype = False
            self.name = False
