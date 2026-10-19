from odoo import fields, models, _
from odoo.exceptions import UserError


class MetaMigrationFieldWizard(models.TransientModel):
    _name = 'meta.migration.field.wizard'
    _description = 'Generate Field Steps Wizard'

    job_id = fields.Many2one('meta.migration.job', required=True)
    model_names = fields.Text(
        string='Source Models', required=True,
        help="One technical model name per line (e.g. sale.order, x_project_task).",
    )
    include_related = fields.Boolean(
        string='Include Related Custom Models', default=True,
        help="Inspect relational fields and auto-include related custom models.",
    )
    create_models = fields.Boolean(
        string='Create Model Steps', default=True,
        help="Add 'create model' step for models that do not already have one.",
    )

    def action_generate(self):
        self.ensure_one()
        job = self.job_id
        rpc = job.source_connection_id._get_rpc(read_only=True)

        raw_lines = [line.strip() for line in (self.model_names or '').splitlines()]
        models_to_process = [m for m in raw_lines if m]
        if not models_to_process:
            raise UserError(_("Please enter at least one model name."))

        final_models = list(models_to_process)

        if self.include_related:
            try:
                rel_fields = rpc.search_read(
                    'ir.model.fields',
                    [
                        ('model', 'in', models_to_process),
                        ('ttype', 'in', ['many2one', 'one2many', 'many2many']),
                        ('relation', '!=', False),
                    ],
                    ['relation'],
                )
                for rf in rel_fields:
                    rel_m = rf.get('relation')
                    if rel_m and rel_m not in final_models:
                        # Check if it is a manual model
                        m_info = rpc.search_read('ir.model', [('model', '=', rel_m)], ['state'], limit=1)
                        if m_info and m_info[0].get('state') == 'manual':
                            final_models.append(rel_m)
            except Exception:
                pass

        existing_steps = job.step_ids
        Step = self.env['meta.migration.step']

        for m in final_models:
            if self.create_models:
                has_model_step = existing_steps.filtered(
                    lambda s: s.object_type == 'model' and s.action == 'create' and s.model_name == m
                )
                if not has_model_step:
                    Step.create({
                        'job_id': job.id,
                        'action': 'create',
                        'object_type': 'model',
                        'model_name': m,
                    })

            has_field_step = existing_steps.filtered(
                lambda s: s.object_type == 'field' and s.action == 'create' and s.model_name == m and not s.field_name
            )
            if not has_field_step:
                Step.create({
                    'job_id': job.id,
                    'action': 'create',
                    'object_type': 'field',
                    'model_name': m,
                    'field_name': False,
                })

        job.action_sort_steps()
        return {'type': 'ir.actions.act_window_close'}
