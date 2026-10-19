import json
from odoo import api, fields, models
from .diff_utils import count_diff


class MetaMigrationChange(models.Model):
    _name = 'meta.migration.change'
    _description = 'Migration Change Record'
    _order = 'run_id, step_index, sequence, id'

    run_id = fields.Many2one('meta.migration.run', required=True, ondelete='cascade', index=True, readonly=True)
    step_id = fields.Many2one('meta.migration.step', ondelete='set null', readonly=True)
    step_index = fields.Integer(readonly=True)
    sequence = fields.Integer(default=10, readonly=True)
    step_label = fields.Char(readonly=True)

    object_type = fields.Selection([
        ('model', 'Model'),
        ('field', 'Field'),
        ('view', 'View'),
        ('server_action', 'Server Action'),
        ('menu', 'Menu'),
        ('access_right', 'Access Right'),
        ('record_rule', 'Record Rule'),
    ], readonly=True)

    change_type = fields.Selection([
        ('create', 'Create'),
        ('update', 'Update'),
        ('unchanged', 'Unchanged'),
        ('exists', 'Exists (Skipped)'),
        ('error', 'Error'),
    ], readonly=True, required=True)

    status = fields.Selection([
        ('planned', 'Planned'),
        ('applied', 'Applied'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ], default='planned', readonly=True, required=True)

    name = fields.Char(readonly=True)
    target_ref = fields.Char(readonly=True)
    old_raw = fields.Text(readonly=True)
    new_raw = fields.Text(readonly=True)

    lines_added = fields.Integer(compute='_compute_lines_diff', store=True, readonly=True)
    lines_removed = fields.Integer(compute='_compute_lines_diff', store=True, readonly=True)

    extra_raw = fields.Text(readonly=True)
    widget_key = fields.Char(compute='_compute_widget_key', store=True)
    children_json = fields.Text(compute='_compute_children_json')

    message = fields.Text(readonly=True)

    @api.depends('old_raw', 'new_raw')
    def _compute_lines_diff(self):
        for rec in self:
            added, removed = count_diff(rec.old_raw, rec.new_raw)
            rec.lines_added = added
            rec.lines_removed = removed

    @api.depends('object_type', 'old_raw')
    def _compute_widget_key(self):
        for rec in self:
            ot = rec.object_type
            has_old = bool((rec.old_raw or '').strip())
            if ot in ('model', 'field', 'view'):
                rec.widget_key = '%s_%s' % (ot, 'update' if has_old else 'create')
            elif ot == 'server_action':
                rec.widget_key = 'server_action'
            elif ot in ('menu', 'access_right', 'record_rule'):
                rec.widget_key = 'generic'
            else:
                rec.widget_key = False

    @api.depends('object_type', 'target_ref', 'run_id')
    def _compute_children_json(self):
        for rec in self:
            rec.children_json = False
            if rec.object_type != 'model' or not rec.target_ref:
                continue
            siblings = self.search([
                ('run_id', '=', rec.run_id.id),
                ('object_type', '=', 'field'),
            ], order='sequence, id')
            out = []
            for c in siblings:
                model, _sep, fname = (c.target_ref or '').rpartition('.')
                if model != rec.target_ref:
                    continue
                try:
                    vals = json.loads(c.new_raw or '{}')
                except Exception:
                    vals = {}
                out.append({
                    'id': c.id,
                    'name': fname,
                    'change_type': c.change_type,
                    'status': c.status,
                    'message': c.message or '',
                    'vals': vals,
                })
            rec.children_json = json.dumps(out, ensure_ascii=False)
