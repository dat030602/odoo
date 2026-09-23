from odoo import fields, models

LINE_STATE = [
    ('pending', 'Pending'),
    ('done', 'Done'),
    ('error', 'Error'),
]


class MetaMigrationModelLine(models.Model):
    _name = 'meta.migration.model.line'
    _description = 'Model to migrate (Meta Migrator)'
    _order = 'sequence, id'

    job_id = fields.Many2one('meta.migration.job', required=True, ondelete='cascade')
    model_name = fields.Char(
        string='Technical Model Name', required=True,
        help="Technical name of the model on the source system, e.g. sale.order or x_my_model.",
    )
    target_model_name = fields.Char(
           string='Target Model Name',
           help="Leave empty to keep the source model name. If a different name is entered, "
               "relations pointing to this model are updated when content is migrated.",
    )
    state = fields.Selection(LINE_STATE, default='pending', readonly=True)
    message = fields.Text(readonly=True)
    sequence = fields.Integer(default=10, help="Order in which model lines are processed.")


class MetaMigrationFieldLine(models.Model):
    _name = 'meta.migration.field.line'
    _description = 'Field to migrate (Meta Migrator)'

    job_id = fields.Many2one('meta.migration.job', required=True, ondelete='cascade')
    model_name = fields.Char(
        string='Technical Model Name', required=True,
        help="Technical name of the source model containing the field, e.g. sale.order.",
    )
    field_name = fields.Char(
        string='Technical Field Name', required=True,
        help="Technical name of the custom field, e.g. x_my_field. Related and computed fields "
             "must reference fields that already exist at the target.",
    )
    state = fields.Selection(LINE_STATE, default='pending', readonly=True)
    message = fields.Text(readonly=True)


class MetaMigrationViewLine(models.Model):
    _name = 'meta.migration.view.line'
    _description = 'View to migrate (Meta Migrator)'

    job_id = fields.Many2one('meta.migration.job', required=True, ondelete='cascade')
    model_name = fields.Char(
        string='Technical Model Name', required=True,
        help="Technical name of the source model whose views should be copied.",
    )
    state = fields.Selection(LINE_STATE, default='pending', readonly=True)
    message = fields.Text(readonly=True)


class MetaMigrationMenuLine(models.Model):
    _name = 'meta.migration.menu.line'
    _description = 'Menu to migrate (Meta Migrator)'

    job_id = fields.Many2one('meta.migration.job', required=True, ondelete='cascade')
    model_name = fields.Char(
        string='Technical Model Name', required=True,
        help="Technical name of the source model whose window actions and menus should be copied.",
    )
    state = fields.Selection(LINE_STATE, default='pending', readonly=True)
    message = fields.Text(readonly=True)


class MetaMigrationActionLine(models.Model):
    _name = 'meta.migration.action.line'
    _description = 'Server Action to migrate (Meta Migrator)'

    job_id = fields.Many2one('meta.migration.job', required=True, ondelete='cascade')
    xml_id = fields.Char(
        string='XML ID', required=True,
        help="Full XML ID of the source server action, e.g. my_module.action_my_action.",
    )
    state = fields.Selection(LINE_STATE, default='pending', readonly=True)
    message = fields.Text(readonly=True)


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
