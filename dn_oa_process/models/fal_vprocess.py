# -*- coding: utf-8 -*-
import logging
import ast

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class fal_vprocess(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    #_order = "sequence"

    _name = "fal.vprocess"
    _description = "Validation Process"

    name = fields.Char("Name", default="Process", tracking=True)
    active = fields.Boolean("Active", default=True, tracking=True)
    
    # @TODO this field is useless as we put the option on the step instead
    disable_edit = fields.Boolean("Disable Edition", default=True, tracking=True)
    
    
    disable_actions = fields.Boolean("Disable Actions", default=True, tracking=True)
    allowed_actions_list = fields.Char("Allowed actions names", default="", tracking=True)
    
    allow_restart_after_approved = fields.Boolean("Allow restart after approved if triggered", default=False, tracking=True)
    allow_restart_after_cancelled = fields.Boolean("Allow restart after cancelled if triggered", default=False, tracking=True)
    
    log_message_to_object = fields.Boolean("Log messages to object", default=False, tracking=True)
    process_activity_type_id = fields.Many2one('mail.activity.type', 'Activity type', required=False, tracking=True)
    
    model_id = fields.Many2one('ir.model', string='Model', tracking=True)
    model_name = fields.Char(string='Model name', related='model_id.model', tracking=True)
    
    trigger_id = fields.Many2one('ir.filters', 'Trigger', required=True, tracking=True)
    trigger_domain = fields.Text(string='Trigger domain', compute='_compute_trigger_domain', tracking=True)
    
    filter_id = fields.Many2one('ir.filters', 'Process-wide filter', required=True, tracking=True)
    filter_domain = fields.Text(string='Process-wide domain', compute='_compute_filter_domain', tracking=True)
    
    step_ids = fields.One2many("fal.vprocess.step", 'process_id', 'Steps', ondelete='cascade')

    count_step = fields.Integer("Count Steps", compute='_compute_count_step', store=True)
    count_rule = fields.Integer("Count Rules", compute='_compute_count_rule', store=True)

    @api.depends('step_ids')
    def _compute_count_step(self):
        for record in self:
            record.count_step = len(record.step_ids)

    @api.depends('step_ids.rule_ids')
    def _compute_count_rule(self):
        for record in self:
            record.count_rule = len(record.mapped('step_ids.rule_ids'))

    def _valid_field_parameter(self, field, name):
        return name == 'ondelete' or super()._valid_field_parameter(field, name)

    #Change related field into compute (Migration V13 - V15), ir_filter changed into single quote when saved in Odoo15
    #JSON.parse() string format must on double quote else error
    #Compute domain to reformat related field
    def _compute_trigger_domain(self):
        for record in self:
            if record.trigger_id and record.trigger_id.domain:
                record.trigger_domain = record.trigger_id.domain.replace("'", '"')
                record.trigger_domain = record.trigger_domain.replace("(", "[")
                record.trigger_domain = record.trigger_domain.replace(")", "]")
            else:
                record.trigger_domain = False

    def _compute_filter_domain(self):
        for record in self:
            if record.filter_id and record.filter_id.domain:
                record.filter_domain = record.filter_id.domain.replace("'", '"')
                record.filter_domain = record.filter_domain.replace("(", "[")
                record.filter_domain = record.filter_domain.replace(")", "]")
            else:
                record.filter_domain = False

    # ------------------------------------------------------------------
    # Server-side helpers used by the web client.
    # These move the "which models have a process" and the domain matching
    # to the server, so the client can (a) lock forms instantly on load via
    # session_info and (b) match records natively instead of parsing domain
    # strings in JS (which was brittle and silently failed).
    # ------------------------------------------------------------------
    @api.model
    def vprocess_models(self):
        """Distinct model names that currently have an active process.

        Injected into ``session_info`` so the web client knows, synchronously
        and with zero RPC, whether a form must be locked while it resolves the
        validation state.
        """
        processes = self.sudo().search([('active', '=', True)])
        return sorted({
            p.model_id.model
            for p in processes
            if p.model_id and p.model_id.model
        })

    @api.model
    def vprocess_bootstrap(self):
        """Return the full active process/step/rule configuration in one shot.

        Injected into ``session_info`` so the web client has the (static) config
        cached at page load, with zero RPC. Only config is included here -- NOT
        the user list, which is large and not needed to decide the lock state.
        Explicit field lists keep the session payload small.
        """
        p_fields = [
            'name', 'active', 'model_id', 'model_name',
            'trigger_id', 'trigger_domain', 'filter_id', 'filter_domain',
            'allow_restart_after_approved', 'allow_restart_after_cancelled',
            'log_message_to_object', 'process_activity_type_id',
            'disable_edit', 'disable_actions', 'allowed_actions_list',
        ]
        s_fields = [
            'name', 'active', 'sequence', 'process_id',
            'disable_edit', 'disable_actions', 'allowed_actions_list',
            'auto_confirm_no_conditions', 'allow_anyone_no_conditions',
            'auto_confirm_no_active_rules', 'enable_email', 'enable_activity',
            'buttons_back', 'buttons_reset',
            'back_to_step_id',
            'action_string_confirm', 'action_string_cancel',
            'action_string_back', 'action_string_reset',
            'field_string_confirm', 'field_string_cancel',
            'field_string_back', 'field_string_reset',
        ]
        r_fields = [
            'id', 'name', 'domain', 'active', 'custom_user_domain',
            'user_ids', 'sequence', 'step_id', 'filter_id', 'user_domain_type', 'server_id',
        ]
        return {
            'processes': self.sudo().search_read(
                [('active', '=', True)], p_fields),
            'steps': self.env['fal.vprocess.step'].sudo().search_read(
                [('active', '=', True)], s_fields, order='sequence asc'),
            'rules': self.env['fal.vprocess.rule'].sudo().search_read(
                [('active', '=', True)], r_fields, order='sequence asc'),
        }

    @api.model
    def _is_empty_filter_domain(self, ir_filter):
        """Return True when a filter has no restricting domain (matches all records)."""
        if not ir_filter:
            return True
        flt = ir_filter.sudo()
        if not flt.exists():
            return True
        domain_str = flt.domain
        if domain_str in (False, None):
            return True
        if isinstance(domain_str, str):
            normalized = domain_str.strip()
            if not normalized or normalized in ('[]', '()'):
                return True
        try:
            eval_domain = flt._get_eval_domain()
        except Exception:
            return False
        return not eval_domain

    @api.model
    def _collect_filter_ids(self, process, rule=None, include_trigger=False):
        """Build the list of ir.filters ids that actually restrict matching."""
        filter_ids = []
        sources = []
        if include_trigger:
            sources.append(process.trigger_id)
        sources.append(process.filter_id)
        if rule:
            sources.append(rule.filter_id)
        for flt in sources:
            if flt and not self._is_empty_filter_domain(flt):
                filter_ids.append(flt.id)
        return filter_ids

    @api.model
    def vp_match(self, model, res_id, filter_ids):
        """Return True if record ``(model, res_id)`` satisfies the AND of the
        domains of every ``ir.filters`` in ``filter_ids``.

        Filters with an empty domain (False, blank, or ``[]``) are ignored and
        therefore match all records. Evaluated with a native ``search_count`` as
        the current user, so record rules and access rights are respected.
        """
        if not model or not res_id or model not in self.env:
            return False
        Filters = self.env['ir.filters'].sudo()
        domain = [('id', '=', int(res_id))]
        for fid in (filter_ids or []):
            if not fid:
                continue
            flt = Filters.browse(int(fid))
            if not flt.exists() or self._is_empty_filter_domain(flt):
                continue
            try:
                domain += flt._get_eval_domain()
            except Exception:
                _logger.warning("vp_match: invalid domain on ir.filters %s", fid)
                return False
        try:
            return bool(self.env[model].search_count(domain))
        except Exception:
            _logger.exception("vp_match: search failed for %s#%s", model, res_id)
            return False

    def _get_process_for_model(self, model_name):
        processes = self.sudo().search([
            ('active', '=', True),
            ('model_name', '=', model_name),
        ])
        if len(processes) > 1:
            raise ValidationError(_("Only one active validation process is allowed for model %s.") % model_name)
        return processes[:1]

    def _get_business_record(self, model_name, record_id):
        if not model_name or model_name not in self.env or not record_id:
            return self.env[model_name] if model_name in self.env else False
        record = self.env[model_name].browse(int(record_id)).exists()
        if not record:
            return False
        record.check_access_rights('read')
        record.check_access_rule('read')
        return record

    def _get_active_execution(self, process, record_id):
        executions = self.env['fal.vprocess.execution'].sudo().search([
            ('process_id', '=', process.id),
            ('target', '=', int(record_id)),
            ('active', '=', True),
        ], order='id desc', limit=2)
        if len(executions) > 1:
            raise ValidationError(_("Multiple active executions exist for record %s.") % record_id)
        return executions[:1]

    def _record_matches(self, process, record):
        return bool(self.vp_match(
            process.model_name,
            record.id,
            self._collect_filter_ids(process, include_trigger=True),
        ))

    def _active_step_rules(self, process, step, record):
        rules = step.rule_ids.filtered('active')
        matching_rules = self.env['fal.vprocess.rule']
        for rule in rules:
            if self.vp_match(
                process.model_name,
                record.id,
                self._collect_filter_ids(process, rule),
            ):
                matching_rules |= rule
        return matching_rules

    def _is_user_authorized(self, process, step, record):
        rules = self._active_step_rules(process, step, record)
        if not rules:
            return step.allow_anyone_no_conditions
        for rule in rules:
            allowed_ids = rule.with_context(
                active_model=process.model_name,
                active_id=record.id,
                active_ids=[record.id],
            ).get_allowed_user_ids()
            if self.env.user.id in allowed_ids:
                return True
        return False

    def _state_without_process(self, reason='not_started'):
        return {
            'has_process': False,
            'started': False,
            'reason': reason,
            'execution_id': False,
            'process_id': False,
            'step_id': False,
            'step_name': False,
            'is_final': False,
            'is_cancelled': False,
            'can_approve': False,
            'can_edit': True,
            'can_use_actions': True,
            'buttons': [],
        }

    @api.model
    def get_approval_state(self, model_name, record_id):
        process = self._get_process_for_model(model_name)
        if not process:
            return self._state_without_process('no_process')
        record = self._get_business_record(model_name, record_id)
        if not record:
            return self._state_without_process('record_not_found')
        steps = process.step_ids.filtered('active').sorted(key=lambda step: (step.sequence, step.id))
        if not steps:
            return self._state_without_process('no_step')

        execution = self._get_active_execution(process, record.id)
        if not execution:
            if not self._record_matches(process, record):
                return self._state_without_process('not_started')
            execution = self.env['fal.vprocess.execution'].sudo().create({
                'name': _('[object #%s] Start process #%s') % (record.id, process.id),
                'target': record.id,
                'process_id': process.id,
                'step_id': steps[0].id,
                'active': True,
            })
            self.env['fal.vprocess.history'].sudo().create({
                'process_id': process.id,
                'execution_id': execution.id,
                'target': record.id,
                'action': 'start',
                'to_step_id': steps[0].id,
            })

        if not self.env['fal.vprocess.history'].sudo().search_count([
            ('execution_id', '=', execution.id),
        ]):
            self.env['fal.vprocess.history'].sudo().create({
                'process_id': process.id,
                'execution_id': execution.id,
                'target': record.id,
                'action': 'start',
                'to_step_id': execution.step_id.id,
                'note': _('Initial history entry'),
            })

        step = execution.step_id
        ordered_steps = steps.filtered(lambda item: item.id != step.id)
        next_step = steps.filtered(lambda item: item.sequence > step.sequence)[:1]
        previous_step = steps.filtered(lambda item: item.sequence < step.sequence)[-1:]
        if step.back_to_step_id in steps:
            previous_step = step.back_to_step_id
        can_approve = not execution.finished and not execution.cancelled and self._is_user_authorized(
            process, step, record
        )
        buttons = []
        if can_approve and not execution.finished and not execution.cancelled:
            buttons.append('confirm')
            if step.buttons_back and previous_step:
                buttons.append('back')
            buttons.append('cancel')
        if execution.finished and process.allow_restart_after_approved and self._record_matches(process, record):
            buttons.append('restart')
        if execution.cancelled and process.allow_restart_after_cancelled and self._record_matches(process, record):
            buttons.append('restart')
        return {
            'has_process': True,
            'started': True,
            'reason': 'active',
            'execution_id': execution.id,
            'process_id': process.id,
            'process_name': process.name,
            'step_id': step.id,
            'step_name': step.name,
            'is_final': execution.finished,
            'is_cancelled': execution.cancelled,
            'can_approve': can_approve,
            'can_edit': not step.disable_edit and not execution.finished and not execution.cancelled,
            'can_use_actions': not step.disable_actions and can_approve,
            'buttons': buttons,
            'next_step_id': next_step.id if next_step else False,
            'previous_step_id': previous_step.id if previous_step else False,
        }

    def _configured_action(self, step, action):
        return (getattr(step, 'action_string_%s' % action, '') or '').split(',')

    def _configured_fields(self, step, action):
        values = {}
        config = getattr(step, 'field_string_%s' % action, '') or ''
        for item in config.split(','):
            if not item.strip() or '=' not in item:
                continue
            field_name, raw_value = item.split('=', 1)
            field_name = field_name.strip()
            if field_name not in step.process_id.env[step.process_id.model_name]._fields:
                raise ValidationError(_("Unknown field in approval configuration: %s") % field_name)
            field = step.process_id.env[step.process_id.model_name]._fields[field_name]
            if field.readonly or field.compute or field.related or field_name in {
                'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
            }:
                raise ValidationError(_("Field %s cannot be updated by approval configuration.") % field_name)
            try:
                values[field_name] = ast.literal_eval(raw_value.strip())
            except (ValueError, SyntaxError):
                values[field_name] = raw_value.strip()
        return values

    def _run_configured_actions(self, record, step, action):
        allowed = set(filter(None, (step.allowed_actions_list or '').replace(' ', '').split(',')))
        for method_name in self._configured_action(step, action):
            method_name = method_name.strip()
            if not method_name:
                continue
            if not allowed or method_name not in allowed or method_name.startswith('_'):
                raise UserError(_("Approval action %s is not allowed by the step whitelist.") % method_name)
            method = getattr(record, method_name, None)
            if not callable(method):
                raise ValidationError(_("Approval action %s does not exist on %s.") % (method_name, record._name))
            method()

    def _approval_ui_payload(self, state):
        color_by_action = {
            'confirm': ('green', 'check'),
            'back': ('black', 'backward'),
            'restart': ('black', 'refresh'),
            'cancel': ('red', 'times'),
            'history': ('blue', 'history'),
        }
        label_by_action = {
            'confirm': _('Approve'),
            'back': _('Back'),
            'restart': _('Restart'),
            'cancel': _('Cancel'),
            'history': _('History'),
        }
        buttons = []
        for action in state.get('buttons', []):
            color, icon = color_by_action[action]
            buttons.append({
                'action': action,
                'label': label_by_action[action],
                'subtitle': '',
                'color': color,
                'icon': icon,
                'enabled': True,
            })
        if state.get('is_final'):
            buttons.append({
                'action': 'approved', 'label': _('Approved'),
                'subtitle': _('Finished'), 'color': 'green',
                'icon': 'check-circle', 'enabled': False,
            })
        elif state.get('is_cancelled'):
            buttons.append({
                'action': 'cancelled', 'label': _('Cancelled'),
                'subtitle': _('Finished'), 'color': 'red',
                'icon': 'times', 'enabled': False,
            })
        elif state.get('has_process') and state.get('started') and not state.get('can_approve'):
            buttons.append({
                'action': 'pending', 'label': _('Pending'),
                'subtitle': _('Approval'), 'color': 'orange',
                'icon': 'warning', 'enabled': False,
            })
        if state.get('has_process') and state.get('started'):
            color, icon = color_by_action['history']
            buttons.append({
                'action': 'history',
                'label': label_by_action['history'],
                'subtitle': '',
                'color': color,
                'icon': icon,
                'enabled': True,
            })
        return {
            'container_id': 'validationProcess_processActionBar',
            'state': state.get('reason', 'not_started'),
            'buttons': buttons,
            'lock_edit': bool(
                state.get('has_process')
                and not state.get('is_final')
                and not state.get('is_cancelled')
                and not state.get('can_edit')
            ),
            'lock_actions': bool(
                state.get('has_process')
                and not state.get('is_final')
                and not state.get('is_cancelled')
                and not state.get('can_use_actions')
            ),
        }

    def _get_history_employee(self, user):
        if not user or 'hr.employee' not in self.env:
            return self.env['res.users']
        if 'employee_ids' in user._fields:
            return user.sudo().employee_ids[:1]
        return self.env['hr.employee']

    def _filter_history_cycle(self, history_records):
        """Keep only entries from the latest approval cycle."""
        records = history_records.sorted('id')
        if not records:
            return records
        cut_idx = -1
        for idx in range(len(records) - 1, -1, -1):
            if records[idx].action in {'cancel', 'restart'}:
                cut_idx = idx
                break
        if cut_idx != -1 and cut_idx < len(records) - 1:
            return records[cut_idx + 1:]
        return records

    def _history_badge_for_action(self, action_code):
        badge_map = {
            'start': ('info', _('Started')),
            'confirm': ('success', _('Approved')),
            'cancel': ('danger', _('Cancelled')),
            'back': ('secondary', _('Back')),
            'restart': ('info', _('Restarted')),
        }
        return badge_map.get(action_code, ('secondary', action_code.replace('_', ' ').title()))

    @api.model
    def _render_approval_history_html(self, model_name, record_id):
        process = self._get_process_for_model(model_name)
        record = self._get_business_record(model_name, record_id)
        if not process or not record:
            return ''
        history = self.env['fal.vprocess.history'].sudo().search([
            ('process_id', '=', process.id),
            ('process_model', '=', model_name),
            ('target', '=', record.id),
        ], order='id asc')
        history = self._filter_history_cycle(history)
        badge_colors = {
            'success': ('#ffffff', '#28a745'),
            'danger': ('#ffffff', '#dc3545'),
            'info': ('#ffffff', '#17a2b8'),
            'secondary': ('#ffffff', '#6c757d'),
        }
        cell_style = 'padding:7px 10px;color:#212529;'
        rows = """
            <table style="width:100%;border-collapse:collapse;font-size:13px;font-family:sans-serif;color:#212529;">
                <thead>
                    <tr style="background:#e9ecef;border-bottom:2px solid #ced4da;">
                        <th class="fw-bold" style="padding:8px 10px;text-align:center;width:50px;color:#212529;">No.</th>
                        <th class="fw-bold" style="padding:8px 10px;text-align:left;color:#212529;">Date</th>
                        <th class="fw-bold" style="padding:8px 10px;text-align:left;color:#212529;">Approver</th>
                        <th class="fw-bold" style="padding:8px 10px;text-align:center;color:#212529;">Status</th>
                    </tr>
                </thead>
                <tbody>
        """
        if not history:
            rows += """
                    <tr style="background:#ffffff;border-bottom:1px solid #dee2e6;">
                        <td colspan="5" style="padding:7px 10px;color:#212529;text-align:center;">No history</td>
                    </tr>
            """
        for idx, item in enumerate(history, start=1):
            employee = self._get_history_employee(item.user_id)
            local_date = fields.Datetime.context_timestamp(self.env.user, item.create_date)
            date_str = local_date.strftime('%Y-%m-%d %H:%M:%S') if local_date else ''
            badge_class, badge_label = self._history_badge_for_action(item.action)
            text_color, bg_color = badge_colors.get(badge_class, ('#ffffff', '#6c757d'))
            badge_html = (
                f'<span style="display:inline-block;padding:3px 10px;border-radius:10px;'
                f'background-color:{bg_color};color:{text_color};'
                f'font-size:11px;font-weight:600;white-space:nowrap;">'
                f'{badge_label}</span>'
            )
            row_bg = '#ffffff' if idx % 2 == 1 else '#f8f9fa'
            rows += f"""
                    <tr style="background:{row_bg};border-bottom:1px solid #dee2e6;">
                        <td style="{cell_style}text-align:center;">{idx}</td>
                        <td style="{cell_style}">{date_str}</td>
                        <td style="{cell_style}">{item.user_id.name or ''}</td>
                        <td style="{cell_style}text-align:center;">{badge_html}</td>
                    </tr>
            """
        rows += """
                </tbody>
            </table>
        """
        return rows

    @api.model
    def get_approval_history(self, model_name, record_id):
        return {'html': self._render_approval_history_html(model_name, record_id)}

    @api.model
    def action_open_approval_history(self, model_name, record_id):
        process = self._get_process_for_model(model_name)
        record = self._get_business_record(model_name, record_id)
        if not process or not record:
            raise UserError(_("No approval history is available for this record."))
        wizard = self.env['fal.vprocess.history.wizard'].create({
            'res_model': model_name,
            'res_id': int(record_id),
            'history_html': self._render_approval_history_html(model_name, record_id),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval History'),
            'res_model': 'fal.vprocess.history.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.model
    def render_approval_bar(self, model_name, record_id):
        state = self.get_approval_state(model_name, record_id)
        payload = self._approval_ui_payload(state)
        if not state.get('has_process') or not state.get('started'):
            payload['html'] = ''
            return payload
        payload['html'] = str(self.env['ir.qweb']._render(
            'dn_oa_process.approval_action_bar',
            {'payload': payload},
        ))
        return payload

    @api.model
    def execute_approval_action(self, model_name, record_id, action):
        if action not in {'confirm', 'cancel', 'back', 'restart'}:
            raise ValidationError(_("Unsupported approval action: %s") % action)
        process = self._get_process_for_model(model_name)
        record = self._get_business_record(model_name, record_id)
        if not process or not record:
            raise UserError(_("No active approval process exists for this record."))
        execution = self._get_active_execution(process, record.id)
        if not execution:
            self.get_approval_state(model_name, record.id)
            execution = self._get_active_execution(process, record.id)
        if not execution:
            raise UserError(_("This record has not started an approval process."))
        execution = execution.exists()
        if not execution:
            raise UserError(_("The approval execution is no longer available."))
        execution.lock_for_update()
        state = self.get_approval_state(model_name, record.id)
        if action not in state['buttons']:
            raise UserError(_("You are not allowed to perform this approval action."))
        step = execution.step_id
        if action == 'confirm':
            next_step = process.step_ids.filtered(
                lambda item: item.active and item.sequence > step.sequence
            ).sorted(key=lambda item: (item.sequence, item.id))[:1]
            values = {'previous_step_id': step.id, 'last_action': action}
            if next_step:
                values['step_id'] = next_step.id
            else:
                values['finished'] = True
        elif action == 'back':
            previous_step = step.back_to_step_id or process.step_ids.filtered(
                lambda item: item.active and item.sequence < step.sequence
            ).sorted(key=lambda item: (item.sequence, item.id))[-1:]
            if not previous_step:
                raise UserError(_("There is no previous approval step."))
            values = {'step_id': previous_step.id, 'previous_step_id': step.id, 'last_action': action}
        elif action == 'restart':
            first_step = process.step_ids.filtered('active').sorted(key=lambda item: (item.sequence, item.id))[:1]
            values = {
                'step_id': first_step.id,
                'previous_step_id': step.id,
                'last_action': action,
                'finished': False,
                'cancelled': False,
            }
        else:
            values = {
                'previous_step_id': step.id,
                'last_action': action,
                'cancelled': True,
            }
        self._run_configured_actions(record, step, action)
        field_values = self._configured_fields(step, action)
        if field_values:
            record.write(field_values)
        execution.write(values)
        self.env['fal.vprocess.history'].sudo().create({
            'process_id': process.id,
            'execution_id': execution.id,
            'target': record.id,
            'action': action,
            'from_step_id': step.id,
            'to_step_id': values.get('step_id') if action != 'cancel' else step.id,
            'note': _('Finished') if values.get('finished') else False,
        })
        if process.log_message_to_object and hasattr(record, 'message_post'):
            record.message_post(body=_('%s: %s step %s') % (process.name, action.upper(), step.name))
        return self.render_approval_bar(model_name, record.id)

    def action_vprocess_step(self):
        self.ensure_one()
        action = self.env.ref('dn_oa_process.action_vprocess_step').sudo().read()[0]
        action['domain'] = [('process_id', '=', self.id)]
        return action

    def action_vprocess_rule(self):
        self.ensure_one()
        action = self.env.ref('dn_oa_process.action_vprocess_rule').sudo().read()[0]
        action['domain'] = [('v_process_id', '=', self.id)]
        return action
