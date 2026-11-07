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


class MetaMigrationJobLine(models.Model):
    _name = 'meta.migration.job.line'
    _description = 'Migrated Object Record with Target XML ID'
    _order = 'job_id, sequence, id'

    job_id = fields.Many2one(
        'meta.migration.job', required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    object_type = fields.Selection([
        ('model', 'Model'),
        ('field', 'Field'),
        ('view', 'View'),
        ('server_action', 'Server Action'),
        ('menu', 'Menu'),
        ('access_right', 'Access Right'),
        ('record_rule', 'Record Rule'),
    ], string='Object Type', required=True)
    model_name = fields.Char(string='Model')
    name = fields.Char(string='Name', required=True)
    xml_id = fields.Char(string='Target XML ID', required=True, index=True)
    target_res_id = fields.Integer(string='Target Record ID')
    state = fields.Selection([
        ('planned', 'Planned'),
        ('applied', 'Applied'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ], string='Status', default='applied')
    last_sync_date = fields.Datetime(string='Last Sync Date', default=fields.Datetime.now)
    message = fields.Text(string='Message')

    _unique_xml_id = models.Constraint(
        'UNIQUE(job_id, xml_id)',
        'Each target XML ID can only be registered once per job.',
    )
