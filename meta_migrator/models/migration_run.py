import json
import logging
import time

import odoo.tools.config
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .rpc_helper import OdooRPCError

_logger = logging.getLogger(__name__)


class MetaMigrationRun(models.Model):
    _name = 'meta.migration.run'
    _description = 'Migration Run (Meta Migrator)'
    _inherit = ['meta.migration.executor', 'meta.migration.planner']
    _order = 'id desc'

    name = fields.Char(string='Run Name', compute='_compute_name', store=True)
    job_id = fields.Many2one('meta.migration.job', string='Job', required=True, ondelete='cascade', index=True)
    mode = fields.Selection([
        ('test', 'Test (Dry Run)'),
        ('run', 'Run (Apply)'),
    ], required=True, readonly=True)

    state = fields.Selection([
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='queued', required=True, index=True)

    source_connection_id = fields.Many2one('meta.migration.connection', string='Source Link', required=True, readonly=True)
    target_connection_id = fields.Many2one('meta.migration.connection', string='Target Link', required=True, readonly=True)
    on_conflict = fields.Selection([
        ('skip', 'Skip if already exists'),
        ('overwrite', 'Overwrite if already exists'),
    ], readonly=True)
    stop_on_error = fields.Boolean(default=True, readonly=True)

    step_data = fields.Text(string='Step Snapshot JSON', readonly=True)
    total_steps = fields.Integer(default=0, readonly=True)
    next_index = fields.Integer(default=0, string='Next Step Index')
    progress = fields.Char(compute='_compute_progress', string='Progress')
    cancel_requested = fields.Boolean(default=False)

    heartbeat = fields.Datetime(readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)

    change_ids = fields.One2many('meta.migration.change', 'run_id', string='Changes')
    summary_text = fields.Char(compute='_compute_summary_text', store=True, string='Summary')
    is_in_sync = fields.Boolean(compute='_compute_summary_text', store=True, string='100% In Sync')
    log_text = fields.Text(string='Log', readonly=True)

    @api.depends('job_id.name', 'mode', 'target_connection_id.name', 'create_date')
    def _compute_name(self):
        for run in self:
            dt_str = fields.Datetime.to_string(run.create_date or fields.Datetime.now())[:19]
            target_str = run.target_connection_id.name or 'Target'
            job_name = run.job_id.name or 'Migration'
            mode_str = 'Test' if run.mode == 'test' else 'Run'
            run.name = f"{job_name} – {mode_str} – {target_str} – {dt_str}"

    @api.depends('total_steps', 'next_index')
    def _compute_progress(self):
        for run in self:
            run.progress = f"{run.next_index}/{run.total_steps}"

    @api.depends('change_ids.change_type', 'mode')
    def _compute_summary_text(self):
        for run in self:
            changes = run.change_ids
            if not changes:
                run.summary_text = _("No changes planned")
                run.is_in_sync = False
                continue

            creates = len(changes.filtered(lambda c: c.change_type == 'create'))
            updates = len(changes.filtered(lambda c: c.change_type == 'update'))
            unchanged = len(changes.filtered(lambda c: c.change_type == 'unchanged'))
            exists = len(changes.filtered(lambda c: c.change_type == 'exists'))
            errors = len(changes.filtered(lambda c: c.change_type == 'error'))

            parts = []
            if creates:
                parts.append(f"+{creates} create")
            if updates:
                parts.append(f"~{updates} update")
            if unchanged:
                parts.append(f"={unchanged} unchanged")
            if exists:
                parts.append(f"{exists} skipped (exists)")
            if errors:
                parts.append(f"!{errors} error")

            run.summary_text = ', '.join(parts) if parts else _("In sync")
            if run.mode == 'test':
                run.is_in_sync = (creates == 0 and updates == 0 and exists == 0 and errors == 0 and unchanged > 0)
            else:
                run.is_in_sync = False

    def action_cancel(self):
        self.ensure_one()
        if self.state in ('queued', 'running'):
            self.write({'cancel_requested': True})
            if self.state == 'queued':
                self.write({'state': 'cancelled', 'finished_at': fields.Datetime.now()})
        return True

    def action_resume(self):
        self.ensure_one()
        if self.state in ('failed', 'cancelled'):
            self.write({
                'state': 'queued',
                'cancel_requested': False,
                'finished_at': False,
            })
            self._enqueue()
        return True

    def _enqueue(self):
        self.ensure_one()
        cron = self.env.ref('meta_migrator.cron_process_runs', raise_if_not_found=False)
        if cron:
            cron._trigger()

    def _safe_commit(self):
        if odoo.tools.config.get('test_enable') or getattr(threading.current_thread(), 'testing', False):
            self.env.cr.flush()
            return
        try:
            self.env.cr.commit()
        except (AssertionError, Exception):
            self.env.cr.flush()

    @api.model
    def _cron_process_runs(self):
        icp = self.env['ir.config_parameter'].sudo()
        budget = int(icp.get_param('meta_migrator.time_budget', 90))
        deadline = time.monotonic() + budget
        while time.monotonic() < deadline:
            run = self._claim_next_run()
            if not run:
                return
            res = run._execute(time_budget=max(deadline - time.monotonic(), 1))
            if res == 'timeout':
                cron = self.env.ref('meta_migrator.cron_process_runs', raise_if_not_found=False)
                if cron:
                    cron._trigger()
                return

    @api.model
    def _claim_next_run(self):
        self.env.cr.execute('''
            SELECT r.id FROM meta_migration_run r
             WHERE (r.state = 'queued'
                    OR (r.state = 'running' AND r.heartbeat < now() AT TIME ZONE 'UTC' - interval '10 minutes'))
               AND NOT EXISTS (SELECT 1 FROM meta_migration_run o
                                WHERE o.target_connection_id = r.target_connection_id
                                  AND o.id <> r.id AND o.state = 'running'
                                  AND o.heartbeat >= now() AT TIME ZONE 'UTC' - interval '10 minutes')
             ORDER BY r.id
             LIMIT 1
               FOR UPDATE SKIP LOCKED
        ''')
        res = self.env.cr.fetchone()
        if not res:
            return None
        run = self.browse(res[0])
        run.write({'state': 'running', 'heartbeat': fields.Datetime.now()})
        self._safe_commit()
        return run

    def _execute(self, time_budget=None):
        self.ensure_one()
        deadline = time.monotonic() + time_budget if time_budget else None
        steps = json.loads(self.step_data or '[]')
        ctx = self._build_ctx(steps)

        self.write({
            'state': 'running',
            'heartbeat': fields.Datetime.now(),
            'started_at': self.started_at or fields.Datetime.now(),
        })
        self._safe_commit()

        i = self.next_index
        had_error = False

        while i < len(steps):
            self.invalidate_recordset(['cancel_requested'])
            if self.cancel_requested:
                return self._finish('cancelled')

            if deadline and time.monotonic() > deadline:
                self.write({'state': 'queued', 'next_index': i})
                self._safe_commit()
                return 'timeout'

            block = self._take_block(steps, i)
            # Remove any changes previously generated from this index onward
            self.change_ids.filtered(lambda c: c.step_index >= i).sudo().unlink()

            ok = self._run_block(block, i, ctx, steps)
            i += len(block)

            self.write({'next_index': i, 'heartbeat': fields.Datetime.now()})
            self._safe_commit()

            had_error = had_error or not ok
            if not ok and self.stop_on_error:
                return self._finish('failed')

        return self._finish('failed' if had_error else 'done')

    def _take_block(self, steps, i):
        if steps[i]['object_type'] == 'field':
            block = []
            j = i
            while j < len(steps) and steps[j]['object_type'] == 'field':
                block.append(steps[j])
                j += 1
            return block
        return [steps[i]]

    def _run_block(self, block, index, ctx, all_steps):
        first = block[0]
        per_step = {}
        try:
            if first['object_type'] == 'field':
                per_step = self._plan_field_block(block, index, ctx)
            else:
                plan_method = getattr(self, f"_plan_{first['object_type']}")
                per_step = {index: plan_method(first, ctx)}
        except (OdooRPCError, UserError, Exception) as e:
            _logger.exception("Error planning block at index %s", index)
            err_dict = {
                'object_type': first['object_type'],
                'change_type': 'error',
                'name': first.get('label') or first.get('object_type'),
                'target_ref': first.get('xml_id') or first.get('model_name') or '',
                'old_raw': '',
                'new_raw': '',
                'message': str(e),
            }
            per_step = {index: [err_dict]}

        all_changes_data = [c for lst in per_step.values() for c in lst]
        created_records = self._record_changes_per_step(per_step, block, index, all_steps)

        has_plan_error = any(c['change_type'] == 'error' for c in all_changes_data)

        if self.mode == 'test':
            return not has_plan_error

        if has_plan_error:
            for rec in created_records:
                if rec.change_type == 'error':
                    rec.sudo().write({'status': 'failed'})
            return False

        # Apply block on target
        try:
            if first['object_type'] == 'field':
                self._apply_field_block(block, ctx)
            else:
                apply_method = getattr(self, f"_apply_{first['object_type']}")
                apply_method(first, ctx)
        except Exception as e:
            _logger.exception("Apply failed for step %s: %s", first.get('label'), e)
            for rec in created_records:
                if rec.change_type in ('create', 'update'):
                    rec.sudo().write({'status': 'failed', 'message': f"Apply error: {e}"})
            return False

        # Mark applied records
        for rec in created_records:
            if rec.change_type in ('create', 'update'):
                rec.sudo().write({'status': 'applied'})
            else:
                rec.sudo().write({'status': 'skipped'})

        return True

    def _record_changes_per_step(self, per_step, block, base_index, all_steps):
        created = self.env['meta.migration.change']
        for step_i, changes in per_step.items():
            step_dict = all_steps[step_i] if step_i < len(all_steps) else block[0]
            step_record_id = step_dict.get('id')
            seq = 10
            for c_vals in changes:
                vals = {
                    'run_id': self.id,
                    'step_id': step_record_id or False,
                    'step_index': step_i,
                    'sequence': seq,
                    'step_label': step_dict.get('label') or '',
                    'object_type': c_vals.get('object_type'),
                    'change_type': c_vals.get('change_type'),
                    'status': 'planned',
                    'name': c_vals.get('name'),
                    'target_ref': c_vals.get('target_ref'),
                    'old_raw': c_vals.get('old_raw') or '',
                    'new_raw': c_vals.get('new_raw') or '',
                    'extra_raw': c_vals.get('extra_raw') or '',
                    'message': c_vals.get('message') or '',
                }
                created |= self.env['meta.migration.change'].sudo().create(vals)
                seq += 10
        return created

    def _finish(self, final_state):
        self.write({
            'state': final_state,
            'finished_at': fields.Datetime.now(),
        })
        self._compute_summary_text()
        return final_state
