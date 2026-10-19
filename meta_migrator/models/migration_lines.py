from odoo import fields, models


class MetaMigrationModelMap(models.Model):
    _name = 'meta.migration.model.map'
    _description = 'Migrated model name mapping'

    source_connection_id = fields.Many2one(
        'meta.migration.connection', required=True, ondelete='cascade',
    )
    target_connection_id = fields.Many2one(
        'meta.migration.connection', required=True, ondelete='cascade',
    )
    source_model = fields.Char(required=True)
    target_model = fields.Char(required=True)

    _unique_mapping = models.Constraint(
        'UNIQUE(source_connection_id, target_connection_id, source_model)',
        'A source model can have only one target mapping for a connection pair.',
    )
