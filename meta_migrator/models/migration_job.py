import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError

SORT_RANK = {
    'model': 10,
    'field': 20,
    'server_action': 30,
    'view': 40,
    'access_right': 50,
    'record_rule': 60,
    'menu': 70,
}


class MetaMigrationJob(models.Model):
    _name = 'meta.migration.job'
    _description = 'Meta Migrator Job Setup'
    _order = 'id desc'

    name = fields.Char(required=True, default=lambda self: _('New Migration'))
    source_connection_id = fields.Many2one(
        'meta.migration.connection', string='Source Link', required=True,
    )
    target_connection_id = fields.Many2one(
        'meta.migration.connection', string='Target Link', required=True,
    )
    on_conflict = fields.Selection([
        ('skip', 'Skip if already exists'),
        ('overwrite', 'Overwrite if already exists'),
    ], default='skip', required=True)

    stop_on_error = fields.Boolean(
        string='Stop on Error', default=True,
        help="If checked, stops execution immediately when a step fails.",
    )
    run_in_background = fields.Boolean(
        string='Run in Background', default=False,
        help="If checked, Test and Run enqueue background tasks processed by cron.",
    )

    step_ids = fields.One2many(
        'meta.migration.step', 'job_id', string='Steps',
    )
    run_ids = fields.One2many(
        'meta.migration.run', 'job_id', string='Runs',
    )

    last_run_id = fields.Many2one(
        'meta.migration.run', compute='_compute_last_run', string='Last Run',
    )
    last_run_summary = fields.Char(
        compute='_compute_last_run', string='Last Run Summary',
    )

    @api.depends('run_ids.summary_text', 'run_ids.state')
    def _compute_last_run(self):
        for job in self:
            last = job.run_ids[:1]
            job.last_run_id = last.id if last else False
            job.last_run_summary = (
                f"[{last.mode.upper()}] {last.summary_text or last.state}" if last else _("No runs yet")
            )

    def _create_run(self, mode):
        self.ensure_one()
        steps = self.step_ids.filtered('active').sorted(lambda s: (s.sequence, s.id))
        if not steps:
            raise UserError(_("The job has no active step."))

        snapshot = [s._to_snapshot() for s in steps]
        return self.env['meta.migration.run'].create({
            'job_id': self.id,
            'mode': mode,
            'source_connection_id': self.source_connection_id.id,
            'target_connection_id': self.target_connection_id.id,
            'on_conflict': self.on_conflict,
            'stop_on_error': self.stop_on_error,
            'step_data': json.dumps(snapshot),
            'total_steps': len(steps),
            'state': 'queued',
        })

    def action_test(self):
        self.ensure_one()
        run = self._create_run('test')
        if self.run_in_background:
            run._enqueue()
        else:
            run._execute(time_budget=None)

        return {
            'name': _('Test Run: %s') % run.name,
            'type': 'ir.actions.act_window',
            'res_model': 'meta.migration.run',
            'res_id': run.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_run(self):
        self.ensure_one()
        run = self._create_run('run')
        if self.run_in_background:
            run._enqueue()
        else:
            run._execute(time_budget=None)

        return {
            'name': _('Migration Run: %s') % run.name,
            'type': 'ir.actions.act_window',
            'res_model': 'meta.migration.run',
            'res_id': run.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_sort_steps(self):
        self.ensure_one()
        steps = self.step_ids.sorted(lambda s: (SORT_RANK.get(s.object_type, 99), s.sequence, s.id))
        for n, step in enumerate(steps, 1):
            step.sequence = n * 10
        return True

    def action_generate_field_steps(self):
        self.ensure_one()
        return {
            'name': _('Generate Field Steps from Models'),
            'type': 'ir.actions.act_window',
            'res_model': 'meta.migration.field.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_id': self.id},
        }
