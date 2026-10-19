import logging
from odoo import api, models, _
from odoo.exceptions import UserError

from .rpc_helper import OdooRPCError
from .diff_utils import dump_json, norm, same, dump_server_action
from . import view_merge

_logger = logging.getLogger(__name__)

FIELD_CORE_KEYS = [
    'name', 'field_description', 'ttype', 'required', 'readonly',
    'store', 'index', 'copied', 'help', 'relation', 'relation_field',
    'on_delete', 'domain', 'selection', 'translate',
]
FIELD_LOGIC_KEYS = ['compute', 'depends', 'related']
ALL_FIELD_KEYS = FIELD_CORE_KEYS + FIELD_LOGIC_KEYS


class MetaMigrationPlanner(models.AbstractModel):
    _name = 'meta.migration.planner'
    _description = 'Migration Planning & Diffing Mixin'

    def _build_ctx(self, steps):
        source_rpc = self.source_connection_id._get_rpc(read_only=True)
        target_rpc = self.target_connection_id._get_rpc(read_only=(self.mode == 'test'))
        cache = {}
        rename_map = self._load_model_map(cache).copy()
        for step in steps:
            if step['object_type'] == 'model':
                src_m = step['model_name']
                tgt_m = step.get('target_model_name') or src_m
                rename_map[src_m] = tgt_m

        return {
            'source_rpc': source_rpc,
            'target_rpc': target_rpc,
            'cache': cache,
            'rename_map': rename_map,
            'dry_run': self.mode == 'test',
            'planned_models': set(),
            'planned_fields': set(),
            'planned_xml_ids': set(),
        }

    def _target_model_state(self, ctx, model_name):
        key = ('tm_state', model_name)
        if key not in ctx['cache']:
            rows = ctx['target_rpc'].search_read('ir.model', [('model', '=', model_name)], ['id'], limit=1)
            ctx['cache'][key] = rows[0]['id'] if rows else False
        if ctx['cache'][key]:
            return 'real', ctx['cache'][key]
        if model_name in ctx['planned_models']:
            return 'virtual', None
        return None, None

    def _plan_model(self, step, ctx):
        src = ctx['source_rpc']
        tgt = ctx['target_rpc']
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)

        src_rows = src.search_read('ir.model', [('model', '=', m)], ['name', 'model', 'state', 'transient'], limit=1)
        if not src_rows:
            if step.get('model_description'):
                src_info = {
                    'name': step['model_description'],
                    'model': m,
                    'state': 'manual',
                    'transient': step.get('transient', False),
                }
            else:
                return [{
                    'object_type': 'model',
                    'change_type': 'error',
                    'name': f"model {m}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': '',
                    'message': _("Model '%s' was not found on the source system.") % m,
                }]
        else:
            src_info = dict(src_rows[0])
            if step.get('model_description'):
                src_info['name'] = step['model_description']
            if 'transient' in step and step['transient']:
                src_info['transient'] = step['transient']

        new_dict = {
            'model': tname,
            'name': src_info['name'],
            'state': 'manual',
            'transient': src_info.get('transient', False),
        }
        new_raw = dump_json(new_dict)

        tgt_rows = tgt.search_read('ir.model', [('model', '=', tname)], ['name', 'model', 'state', 'transient'], limit=1)
        if not tgt_rows:
            if src_info.get('state') != 'manual':
                return [{
                    'object_type': 'model',
                    'change_type': 'error',
                    'name': f"model {tname}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Standard model '%s' does not exist on target. Install its module on target first.") % m,
                }]
            ctx['planned_models'].add(tname)
            extra_raw = dump_json({'source_model': m}) if m != tname else ''
            return [{
                'object_type': 'model',
                'change_type': 'create',
                'name': f"model {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': new_raw,
                'extra_raw': extra_raw,
                'message': _("Create custom model %s") % tname,
            }]

        tgt_info = tgt_rows[0]
        old_dict = {
            'model': tgt_info['model'],
            'name': tgt_info['name'],
            'state': tgt_info['state'],
            'transient': tgt_info.get('transient', False),
        }
        old_raw = dump_json(old_dict)

        if same(old_dict, new_dict, ['name', 'transient']):
            change_type = 'unchanged'
            msg = _("Model '%s' already exists at target (in sync).") % tname
        else:
            change_type = 'exists'
            msg = _("Model '%s' already exists at target; attributes differ but model updates are skipped.") % tname

        extra_raw = dump_json({'source_model': m}) if m != tname else ''
        return [{
            'object_type': 'model',
            'change_type': change_type,
            'name': f"model {tname}",
            'target_ref': tname,
            'old_raw': old_raw,
            'new_raw': new_raw,
            'extra_raw': extra_raw,
            'message': msg,
        }]

    def _plan_field_block(self, block, base_index, ctx):
        items = []
        for offset, step in enumerate(block):
            step_i = base_index + offset
            m = step['model_name']
            fname = step['field_name']
            tmodel = ctx['rename_map'].get(m, m)

            if step.get('ttype'):
                fvals = {
                    'name': fname,
                    'field_description': step.get('field_description') or fname,
                    'ttype': step.get('ttype'),
                    'required': step.get('required', False),
                    'readonly': step.get('readonly', False),
                    'store': step.get('store', True),
                    'index': step.get('index', False),
                    'copied': step.get('copied', True),
                    'help': step.get('help') or False,
                    'relation': step.get('relation') or False,
                    'relation_field': step.get('relation_field') or False,
                    'on_delete': step.get('on_delete') or False,
                    'selection': step.get('selection') or False,
                    'translate': step.get('translate', False),
                    'compute': step.get('compute') or False,
                    'depends': step.get('depends') or False,
                    'related': step.get('related') or False,
                    'state': 'manual',
                }
                items.append({
                    'step_i': step_i,
                    'model_name': m,
                    'tmodel': tmodel,
                    'fvals': fvals,
                })
            else:
                domain = [('model', '=', m), ('state', '=', 'manual')]
                if fname:
                    domain.append(('name', '=', fname))
                fields_data = ctx['source_rpc'].search_read('ir.model.fields', domain, ALL_FIELD_KEYS)
                if fname and not fields_data:
                    # Specific field requested but not found
                    items.append({
                        'step_i': step_i,
                        'model_name': m,
                        'tmodel': tmodel,
                        'fvals': None,
                        'missing_fname': fname,
                    })
                else:
                    for fvals in fields_data:
                        items.append({
                            'step_i': step_i,
                            'model_name': m,
                            'tmodel': tmodel,
                            'fvals': fvals,
                        })

        declared = {(it['tmodel'], it['fvals']['name']) for it in items if it.get('fvals')}
        out = {}

        for it in items:
            if not it.get('fvals'):
                err_change = {
                    'object_type': 'field',
                    'change_type': 'error',
                    'name': f"field {it['tmodel']}.{it['missing_fname']}",
                    'target_ref': f"{it['tmodel']}.{it['missing_fname']}",
                    'old_raw': '',
                    'new_raw': '',
                    'message': _("Field '%s.%s' not found on source or state != manual.") % (it['model_name'], it['missing_fname']),
                }
                out.setdefault(it['step_i'], []).append(err_change)
                continue

            change = self._plan_one_field(it, ctx)
            err = self._check_relations(it, declared, ctx)
            if err:
                change['change_type'] = 'error'
                change['message'] = (change['message'] + ' | ' if change.get('message') else '') + err
            out.setdefault(it['step_i'], []).append(change)

        return out

    def _check_relations(self, it, declared, ctx):
        fvals = it['fvals']
        ttype = fvals.get('ttype')
        rename_map = ctx['rename_map']

        if ttype in ('many2one', 'one2many', 'many2many') and fvals.get('relation'):
            rel_source = fvals['relation']
            rel_target = rename_map.get(rel_source, rel_source)
            st, _target_mid = self._target_model_state(ctx, rel_target)
            if not st:
                return _("Target relational model '%s' does not exist on target and has no preceding create step.") % rel_target

        if ttype == 'one2many':
            rel_source = fvals.get('relation')
            rel_target = rename_map.get(rel_source, rel_source)
            rel_field = fvals.get('relation_field')
            if not rel_field:
                return _("One2many field '%s' is missing relation_field.") % fvals['name']
            if (rel_target, rel_field) not in declared:
                st, tmid = self._target_model_state(ctx, rel_target)
                exists_on_tgt = False
                if st == 'real':
                    existing = ctx['target_rpc'].search_read(
                        'ir.model.fields',
                        [('model_id', '=', tmid), ('name', '=', rel_field)],
                        ['id'], limit=1,
                    )
                    exists_on_tgt = bool(existing)
                elif (rel_target, rel_field) in ctx['planned_fields']:
                    exists_on_tgt = True
                if not exists_on_tgt:
                    return _("Relation field '%s' for one2many does not exist on model '%s'. Add step to create field '%s' on '%s'.") % (
                        rel_field, rel_target, rel_field, rel_target,
                    )
        return None

    def _plan_one_field(self, it, ctx):
        fvals = it['fvals']
        tmodel = it['tmodel']
        fname = fvals['name']
        new_vals = self._build_field_vals(fvals, ctx['rename_map'])
        for k in FIELD_LOGIC_KEYS:
            if fvals.get(k):
                new_vals[k] = fvals[k]

        new_raw = dump_json(new_vals)
        st, tmid = self._target_model_state(ctx, tmodel)

        tgt_field = None
        if st == 'real':
            existing = ctx['target_rpc'].search_read(
                'ir.model.fields',
                [('model_id', '=', tmid), ('name', '=', fname)],
                list(new_vals.keys()), limit=1,
            )
            if existing:
                tgt_field = existing[0]

        if not tgt_field:
            ctx['planned_fields'].add((tmodel, fname))
            return {
                'object_type': 'field',
                'change_type': 'create',
                'name': f"field {tmodel}.{fname}",
                'target_ref': f"{tmodel}.{fname}",
                'old_raw': '',
                'new_raw': new_raw,
                'message': _("New field to create"),
            }

        old_vals = {k: tgt_field.get(k) for k in new_vals}
        old_raw = dump_json(old_vals)

        diff_keys = [k for k in new_vals if norm(old_vals.get(k)) != norm(new_vals.get(k))]
        if not diff_keys:
            change_type = 'unchanged'
            msg = _("Field matches target definition exactly.")
        else:
            if self.on_conflict == 'overwrite':
                change_type = 'update'
                msg = _("Differing attributes: %s. Will overwrite.") % ', '.join(diff_keys)
            else:
                change_type = 'exists'
                msg = _("Differing attributes: %s. Skipped due to conflict policy.") % ', '.join(diff_keys)

        return {
            'object_type': 'field',
            'change_type': change_type,
            'name': f"field {tmodel}.{fname}",
            'target_ref': f"{tmodel}.{fname}",
            'old_raw': old_raw,
            'new_raw': new_raw,
            'message': msg,
        }

    def _plan_view(self, step, ctx):
        if step.get('action') == 'update':
            return self._plan_view_update(step, ctx)
        return self._plan_view_create(step, ctx)

    def _plan_view_create(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        vtype = step['view_type']
        search_types = [vtype] if vtype != 'list' else ['list', 'tree']

        st, _tmid = self._target_model_state(ctx, tname)
        if not st:
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"view {vtype} on {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("Target model '%s' does not exist and has no preceding create step.") % tname,
            }]

        if step.get('arch'):
            view_name = step.get('view_name') or f"{vtype} view on {tname}"
            new_raw = (step['arch'] or '').strip()
            v_extra = dump_json({
                'name': view_name,
                'type': vtype,
                'model': tname,
                'priority': step.get('priority', 16),
                'inherit_name': step.get('inherit_xml_id') or False,
            })
            existing = ctx['target_rpc'].search_read(
                'ir.ui.view',
                [('model', '=', tname), ('type', '=', vtype), ('name', '=', view_name)],
                ['id', 'arch'], limit=1,
            )
            if not existing:
                return [{
                    'object_type': 'view',
                    'change_type': 'create',
                    'name': f"view {vtype} on {tname}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'extra_raw': v_extra,
                    'message': _("Create new %s view for %s") % (vtype, tname),
                }]

            old_raw = (existing[0].get('arch') or '').strip()
            if view_merge.canonical_text(new_raw) == view_merge.canonical_text(old_raw):
                change_type = 'unchanged'
                msg = _("View '%s' already exists and matches source arch.") % view_name
            else:
                if self.on_conflict == 'overwrite':
                    change_type = 'update'
                    msg = _("View arch differs; will overwrite.")
                else:
                    change_type = 'exists'
                    msg = _("View arch differs; skipped due to conflict policy.")

            return [{
                'object_type': 'view',
                'change_type': change_type,
                'name': f"view {vtype} on {tname}",
                'target_ref': tname,
                'old_raw': old_raw,
                'new_raw': new_raw,
                'extra_raw': v_extra,
                'message': msg,
            }]

        views = ctx['source_rpc'].search_read(
            'ir.ui.view',
            [('model', '=', m), ('type', 'in', search_types), ('active', '=', True)],
            ['name', 'type', 'arch', 'priority', 'inherit_id'],
        )
        if not views:
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"view {vtype} on {m}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("View '%s' for model '%s' not found on source.") % (vtype, m),
            }]

        views.sort(key=lambda v: v.get('priority', 16))
        view = views[0]
        new_raw = (view.get('arch') or '').strip()
        v_extra = dump_json({
            'name': view['name'],
            'type': vtype,
            'model': tname,
            'priority': view.get('priority', 16),
            'inherit_name': (view.get('inherit_id') or [None, None])[1],
        })

        existing = ctx['target_rpc'].search_read(
            'ir.ui.view',
            [('model', '=', tname), ('type', '=', vtype), ('name', '=', view['name'])],
            ['id', 'arch'], limit=1,
        )
        if not existing:
            return [{
                'object_type': 'view',
                'change_type': 'create',
                'name': f"view {vtype} on {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': new_raw,
                'extra_raw': v_extra,
                'message': _("Create new %s view for %s") % (vtype, tname),
            }]

        old_raw = (existing[0].get('arch') or '').strip()
        if view_merge.canonical_text(new_raw) == view_merge.canonical_text(old_raw):
            change_type = 'unchanged'
            msg = _("View '%s' already exists and matches source arch.") % view['name']
        else:
            if self.on_conflict == 'overwrite':
                change_type = 'update'
                msg = _("View arch differs; will overwrite.")
            else:
                change_type = 'exists'
                msg = _("View arch differs; skipped due to conflict policy.")

        return [{
            'object_type': 'view',
            'change_type': change_type,
            'name': f"view {vtype} on {tname}",
            'target_ref': tname,
            'old_raw': old_raw,
            'new_raw': new_raw,
            'extra_raw': v_extra,
            'message': msg,
        }]

    def _plan_view_update(self, step, ctx):
        xml_id = step['xml_id']
        module, name = xml_id.split('.', 1)

        src_data = ctx['source_rpc'].search_read('ir.model.data', [('module', '=', module), ('name', '=', name)], ['res_id', 'model'], limit=1)
        if not src_data or src_data[0]['model'] != 'ir.ui.view':
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"update view {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("View with XML ID '%s' not found on source.") % xml_id,
            }]

        src_view = ctx['source_rpc'].read('ir.ui.view', [src_data[0]['res_id']], ['arch', 'inherit_id', 'model'])[0]

        tgt_data = ctx['target_rpc'].search_read('ir.model.data', [('module', '=', module), ('name', '=', name)], ['res_id', 'model'], limit=1)
        if not tgt_data or tgt_data[0]['model'] != 'ir.ui.view':
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"update view {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("View with XML ID '%s' does not exist on target system. Update step requires existing target view.") % xml_id,
            }]

        tgt_view = ctx['target_rpc'].read('ir.ui.view', [tgt_data[0]['res_id']], ['arch', 'inherit_id', 'model'])[0]

        res = view_merge.plan_append(src_view['arch'], tgt_view['arch'], bool(src_view.get('inherit_id')), bool(tgt_view.get('inherit_id')))
        if res.error:
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"update view {xml_id}",
                'target_ref': xml_id,
                'old_raw': res.old_view_text,
                'new_raw': '',
                'message': res.error,
            }]

        if not res.added:
            extra_raw = dump_json({
                'added': [],
                'present': view_merge.serialize(res.present),
                'wrapped': res.wrapped,
            })
            return [{
                'object_type': 'view',
                'change_type': 'unchanged',
                'name': f"update view {xml_id}",
                'target_ref': xml_id,
                'old_raw': res.old_view_text,
                'new_raw': res.old_view_text,
                'extra_raw': extra_raw,
                'message': _("All elements are already present in target view arch (in sync)."),
            }]

        extra_raw = dump_json({
            'added': view_merge.serialize(res.added),
            'present': view_merge.serialize(res.present),
            'wrapped': res.wrapped,
        })
        wrap_note = " (wrapped in <data>)" if res.wrapped else ""
        return [{
            'object_type': 'view',
            'change_type': 'update',
            'name': f"update view {xml_id}",
            'target_ref': xml_id,
            'old_raw': res.old_view_text,
            'new_raw': res.new_arch,
            'extra_raw': extra_raw,
            'message': _("Appending %d new elements to <data>%s.") % (len(res.added), wrap_note),
        }]

    def _plan_server_action(self, step, ctx):
        xml_id = step['xml_id']
        module, name = xml_id.split('.', 1)

        if step.get('code') or step.get('action_name'):
            tgt_m = ctx['rename_map'].get(step.get('model_name'), step.get('model_name')) if step.get('model_name') else ''
            tgt_bm = ctx['rename_map'].get(step.get('binding_model'), step.get('binding_model')) if step.get('binding_model') else ''
            new_dict = {
                'name': step.get('action_name') or name,
                'state': step.get('state') or 'code',
                'model': tgt_m,
                'binding_model': tgt_bm,
                'binding_type': step.get('binding_type') or 'action',
                'code': step.get('code') or '',
            }
            new_raw = dump_server_action(new_dict)

            tgt_data = ctx['target_rpc'].search_read('ir.model.data', [('module', '=', module), ('name', '=', name)], ['res_id', 'model'], limit=1)
            if not tgt_data:
                if step['action'] == 'update':
                    return [{
                        'object_type': 'server_action',
                        'change_type': 'error',
                        'name': f"server action {xml_id}",
                        'target_ref': xml_id,
                        'old_raw': '',
                        'new_raw': new_raw,
                        'message': _("Server action does not exist on target. Use a Create step instead of Update."),
                    }]
                ctx['planned_xml_ids'].add(xml_id)
                return [{
                    'object_type': 'server_action',
                    'change_type': 'create',
                    'name': f"server action {xml_id}",
                    'target_ref': xml_id,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Create server action %s") % xml_id,
                }]

            tgt_action = ctx['target_rpc'].read('ir.actions.server', [tgt_data[0]['res_id']], ['name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'])[0]
            cur_m = self._read_model_name(ctx['target_rpc'], tgt_action.get('model_id')) or ''
            cur_bm = self._read_model_name(ctx['target_rpc'], tgt_action.get('binding_model_id')) or ''
            old_dict = {
                'name': tgt_action['name'],
                'state': tgt_action.get('state') or 'code',
                'model': cur_m,
                'binding_model': cur_bm,
                'binding_type': tgt_action.get('binding_type') or 'action',
                'code': tgt_action.get('code') or '',
            }
            old_raw = dump_server_action(old_dict)

            if old_raw == new_raw:
                change_type = 'unchanged'
                msg = _("Server action matches target exactly.")
            else:
                if step['action'] == 'update' or self.on_conflict == 'overwrite':
                    change_type = 'update'
                    msg = _("Server action differs; will overwrite.")
                else:
                    change_type = 'exists'
                    msg = _("Server action differs; skipped due to conflict policy.")

            return [{
                'object_type': 'server_action',
                'change_type': change_type,
                'name': f"server action {xml_id}",
                'target_ref': xml_id,
                'old_raw': old_raw,
                'new_raw': new_raw,
                'message': msg,
            }]

        src_data = ctx['source_rpc'].search_read('ir.model.data', [('module', '=', module), ('name', '=', name)], ['res_id', 'model'], limit=1)
        if not src_data or src_data[0]['model'] != 'ir.actions.server':
            return [{
                'object_type': 'server_action',
                'change_type': 'error',
                'name': f"server action {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Server Action with XML ID '%s' not found on source.") % xml_id,
            }]

        res_id = src_data[0]['res_id']
        action = ctx['source_rpc'].read('ir.actions.server', [res_id], ['name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'])[0]

        src_m = self._read_model_name(ctx['source_rpc'], action.get('model_id'))
        src_bm = self._read_model_name(ctx['source_rpc'], action.get('binding_model_id'))
        tgt_m = ctx['rename_map'].get(src_m, src_m) if src_m else ''
        tgt_bm = ctx['rename_map'].get(src_bm, src_bm) if src_bm else ''

        new_dict = {
            'name': action['name'],
            'state': action.get('state') or 'code',
            'model': tgt_m,
            'binding_model': tgt_bm,
            'binding_type': action.get('binding_type') or 'action',
            'code': action.get('code') or '',
        }
        new_raw = dump_server_action(new_dict)

        tgt_data = ctx['target_rpc'].search_read('ir.model.data', [('module', '=', module), ('name', '=', name)], ['res_id', 'model'], limit=1)
        if not tgt_data:
            if step['action'] == 'update':
                return [{
                    'object_type': 'server_action',
                    'change_type': 'error',
                    'name': f"server action {xml_id}",
                    'target_ref': xml_id,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Server action does not exist on target. Use a Create step instead of Update."),
                }]
            ctx['planned_xml_ids'].add(xml_id)
            return [{
                'object_type': 'server_action',
                'change_type': 'create',
                'name': f"server action {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': new_raw,
                'message': _("Create server action %s") % xml_id,
            }]

        tgt_action = ctx['target_rpc'].read('ir.actions.server', [tgt_data[0]['res_id']], ['name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'])[0]
        cur_m = self._read_model_name(ctx['target_rpc'], tgt_action.get('model_id')) or ''
        cur_bm = self._read_model_name(ctx['target_rpc'], tgt_action.get('binding_model_id')) or ''
        old_dict = {
            'name': tgt_action['name'],
            'state': tgt_action.get('state') or 'code',
            'model': cur_m,
            'binding_model': cur_bm,
            'binding_type': tgt_action.get('binding_type') or 'action',
            'code': tgt_action.get('code') or '',
        }
        old_raw = dump_server_action(old_dict)

        if old_raw == new_raw:
            change_type = 'unchanged'
            msg = _("Server action matches target exactly.")
        else:
            if step['action'] == 'update' or self.on_conflict == 'overwrite':
                change_type = 'update'
                msg = _("Server action differs; will overwrite.")
            else:
                change_type = 'exists'
                msg = _("Server action differs; skipped due to conflict policy.")

        return [{
            'object_type': 'server_action',
            'change_type': change_type,
            'name': f"server action {xml_id}",
            'target_ref': xml_id,
            'old_raw': old_raw,
            'new_raw': new_raw,
            'message': msg,
        }]

    def _plan_menu(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        actions = ctx['source_rpc'].search_read(
            'ir.actions.act_window', [('res_model', '=', m)], [
                'name', 'res_model', 'view_mode', 'domain', 'context', 'limit', 'target', 'help',
            ],
        )
        if not actions:
            return [{
                'object_type': 'menu',
                'change_type': 'unchanged',
                'name': f"menus for {m}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("No window action found on source for model %s.") % m,
            }]

        changes = []
        for src_act in actions:
            # Plan window action
            act_vals = {
                'name': src_act['name'],
                'res_model': tname,
                'view_mode': src_act.get('view_mode') or 'list,form',
                'domain': src_act.get('domain') or '[]',
                'context': src_act.get('context') or '{}',
                'limit': src_act.get('limit', 80),
                'target': src_act.get('target') or 'current',
            }
            new_act_raw = dump_json(act_vals)

            existing_act = ctx['target_rpc'].search_read(
                'ir.actions.act_window', [('name', '=', src_act['name']), ('res_model', '=', tname)],
                list(act_vals.keys()), limit=1,
            )
            if not existing_act:
                act_change_type = 'create'
                act_old_raw = ''
                act_msg = _("Create window action '%s'") % src_act['name']
            else:
                old_act_dict = {k: existing_act[0].get(k) for k in act_vals}
                act_old_raw = dump_json(old_act_dict)
                if same(old_act_dict, act_vals, list(act_vals.keys())):
                    act_change_type = 'unchanged'
                    act_msg = _("Window action in sync.")
                else:
                    act_change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
                    act_msg = _("Window action differs.")

            changes.append({
                'object_type': 'menu',
                'change_type': act_change_type,
                'name': f"window action: {src_act['name']}",
                'target_ref': tname,
                'old_raw': act_old_raw,
                'new_raw': new_act_raw,
                'message': act_msg,
            })

            # Check related menus
            menus = ctx['source_rpc'].search_read(
                'ir.ui.menu', [('action', '=', 'ir.actions.act_window,%s' % src_act['id'])],
                ['name', 'parent_id', 'sequence', 'active', 'web_icon'],
            )
            for m_item in menus:
                m_vals = {
                    'name': m_item['name'],
                    'sequence': m_item.get('sequence', 10),
                    'active': m_item.get('active', True),
                    'action': f"ir.actions.act_window for {tname}",
                }
                new_m_raw = dump_json(m_vals)

                tgt_m_recs = ctx['target_rpc'].search_read(
                    'ir.ui.menu', [('name', '=', m_item['name'])],
                    ['id', 'name', 'sequence', 'active'], limit=1,
                )
                if not tgt_m_recs:
                    m_change_type = 'create'
                    m_old_raw = ''
                    m_msg = _("Create menu '%s'") % m_item['name']
                else:
                    old_m_dict = {
                        'name': tgt_m_recs[0]['name'],
                        'sequence': tgt_m_recs[0].get('sequence', 10),
                        'active': tgt_m_recs[0].get('active', True),
                        'action': f"ir.actions.act_window for {tname}",
                    }
                    m_old_raw = dump_json(old_m_dict)
                    if same(old_m_dict, m_vals, ['name', 'sequence', 'active']):
                        m_change_type = 'unchanged'
                        m_msg = _("Menu in sync.")
                    else:
                        m_change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
                        m_msg = _("Menu differs.")

                changes.append({
                    'object_type': 'menu',
                    'change_type': m_change_type,
                    'name': f"menu: {m_item['name']}",
                    'target_ref': tname,
                    'old_raw': m_old_raw,
                    'new_raw': new_m_raw,
                    'message': m_msg,
                })

        return changes

    def _plan_access_right(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)

        if step.get('access_name'):
            group_ref = step.get('group_xml_id') or 'All'
            new_vals = {
                'name': step['access_name'],
                'model': tname,
                'group': group_ref,
                'perm_read': step.get('perm_read', False),
                'perm_write': step.get('perm_write', False),
                'perm_create': step.get('perm_create', False),
                'perm_unlink': step.get('perm_unlink', False),
            }
            new_raw = dump_json(new_vals)
            st, tmid = self._target_model_state(ctx, tname)
            existing = None
            if st == 'real':
                domain = [('model_id', '=', tmid), ('name', '=', step['access_name'])]
                res = ctx['target_rpc'].search_read(
                    'ir.model.access', domain,
                    ['name', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'], limit=1,
                )
                if res:
                    existing = res[0]

            if not existing:
                return [{
                    'object_type': 'access_right',
                    'change_type': 'create',
                    'name': f"access {step['access_name']}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Create access right"),
                }]
            else:
                tgt_gid = existing.get('group_id')
                tgt_g_ref = self._get_xml_id(ctx['target_rpc'], 'res.groups', tgt_gid[0], ctx['cache']) if tgt_gid else 'All'
                old_vals = {
                    'name': existing['name'],
                    'model': tname,
                    'group': tgt_g_ref,
                    'perm_read': existing.get('perm_read', False),
                    'perm_write': existing.get('perm_write', False),
                    'perm_create': existing.get('perm_create', False),
                    'perm_unlink': existing.get('perm_unlink', False),
                }
                old_raw = dump_json(old_vals)
                if same(old_vals, new_vals, list(new_vals.keys())):
                    change_type = 'unchanged'
                    msg = _("Access right in sync.")
                else:
                    change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
                    msg = _("Access right differs.")

                return [{
                    'object_type': 'access_right',
                    'change_type': change_type,
                    'name': f"access {step['access_name']}",
                    'target_ref': tname,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'message': msg,
                }]

        access_records = ctx['source_rpc'].search_read(
            'ir.model.access', [('model_id.model', '=', m)], [
                'name', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'],
        )
        if not access_records:
            return [{
                'object_type': 'access_right',
                'change_type': 'unchanged',
                'name': f"access rights for {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("No access rights found on source for model %s.") % m,
            }]

        changes = []
        for acc in access_records:
            source_group = acc.get('group_id')
            source_group_id = source_group[0] if source_group else False
            target_group_id = self._map_group_id(ctx['source_rpc'], ctx['target_rpc'], source_group_id, ctx['cache'])

            group_ref = self._get_xml_id(ctx['source_rpc'], 'res.groups', source_group_id, ctx['cache']) if source_group_id else 'All'
            new_vals = {
                'name': acc['name'],
                'model': tname,
                'group': group_ref,
                'perm_read': acc.get('perm_read', False),
                'perm_write': acc.get('perm_write', False),
                'perm_create': acc.get('perm_create', False),
                'perm_unlink': acc.get('perm_unlink', False),
            }
            new_raw = dump_json(new_vals)

            if source_group_id and not target_group_id:
                changes.append({
                    'object_type': 'access_right',
                    'change_type': 'exists',
                    'name': f"access {acc['name']}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Source group '%s' cannot be mapped on target link; skipped.") % group_ref,
                })
                continue

            st, tmid = self._target_model_state(ctx, tname)
            existing = None
            if st == 'real':
                domain = [('model_id', '=', tmid), ('name', '=', acc['name'])]
                res = ctx['target_rpc'].search_read(
                    'ir.model.access', domain,
                    ['name', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'], limit=1,
                )
                if res:
                    existing = res[0]

            if not existing:
                changes.append({
                    'object_type': 'access_right',
                    'change_type': 'create',
                    'name': f"access {acc['name']}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Create access right"),
                })
            else:
                tgt_gid = existing.get('group_id')
                tgt_g_ref = self._get_xml_id(ctx['target_rpc'], 'res.groups', tgt_gid[0], ctx['cache']) if tgt_gid else 'All'
                old_vals = {
                    'name': existing['name'],
                    'model': tname,
                    'group': tgt_g_ref,
                    'perm_read': existing.get('perm_read', False),
                    'perm_write': existing.get('perm_write', False),
                    'perm_create': existing.get('perm_create', False),
                    'perm_unlink': existing.get('perm_unlink', False),
                }
                old_raw = dump_json(old_vals)
                if same(old_vals, new_vals, list(new_vals.keys())):
                    change_type = 'unchanged'
                    msg = _("Access right in sync.")
                else:
                    change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
                    msg = _("Access right differs.")

                changes.append({
                    'object_type': 'access_right',
                    'change_type': change_type,
                    'name': f"access {acc['name']}",
                    'target_ref': tname,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'message': msg,
                })

        return changes

    def _plan_record_rule(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)

        if step.get('rule_name'):
            group_ref = [step.get('group_xml_id')] if step.get('group_xml_id') else []
            new_vals = {
                'name': step['rule_name'],
                'model': tname,
                'domain_force': step.get('domain_force') or '',
                'groups': group_ref,
                'perm_read': step.get('perm_read', False),
                'perm_write': step.get('perm_write', False),
                'perm_create': step.get('perm_create', False),
                'perm_unlink': step.get('perm_unlink', False),
                'active': step.get('rule_active', True),
            }
            new_raw = dump_json(new_vals)
            st, tmid = self._target_model_state(ctx, tname)
            existing = None
            if st == 'real':
                res = ctx['target_rpc'].search_read(
                    'ir.rule', [('model_id', '=', tmid), ('name', '=', step['rule_name'])],
                    ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'], limit=1,
                )
                if res:
                    existing = res[0]

            if not existing:
                return [{
                    'object_type': 'record_rule',
                    'change_type': 'create',
                    'name': f"rule {step['rule_name']}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Create record rule"),
                }]
            else:
                tgt_gids = existing.get('groups') or []
                tgt_grefs = sorted([self._get_xml_id(ctx['target_rpc'], 'res.groups', gid, ctx['cache']) or f"id:{gid}" for gid in tgt_gids])
                old_vals = {
                    'name': existing['name'],
                    'model': tname,
                    'domain_force': existing.get('domain_force') or '',
                    'groups': tgt_grefs,
                    'perm_read': existing.get('perm_read', False),
                    'perm_write': existing.get('perm_write', False),
                    'perm_create': existing.get('perm_create', False),
                    'perm_unlink': existing.get('perm_unlink', False),
                    'active': existing.get('active', True),
                }
                old_raw = dump_json(old_vals)
                if same(old_vals, new_vals, ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active']):
                    change_type = 'unchanged'
                    msg = _("Record rule in sync.")
                else:
                    change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
                    msg = _("Record rule differs.")

                return [{
                    'object_type': 'record_rule',
                    'change_type': change_type,
                    'name': f"rule {step['rule_name']}",
                    'target_ref': tname,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'message': msg,
                }]

        rules = ctx['source_rpc'].search_read(
            'ir.rule', [('model_id.model', '=', m)], [
                'name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active',
            ],
        )
        if not rules:
            return [{
                'object_type': 'record_rule',
                'change_type': 'unchanged',
                'name': f"record rules for {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("No record rules found on source for model %s.") % m,
            }]

        changes = []
        for r in rules:
            src_gids = r.get('groups') or []
            src_grefs = sorted([self._get_xml_id(ctx['source_rpc'], 'res.groups', gid, ctx['cache']) or f"id:{gid}" for gid in src_gids])
            new_vals = {
                'name': r['name'],
                'model': tname,
                'domain_force': r.get('domain_force') or '',
                'groups': src_grefs,
                'perm_read': r.get('perm_read', False),
                'perm_write': r.get('perm_write', False),
                'perm_create': r.get('perm_create', False),
                'perm_unlink': r.get('perm_unlink', False),
                'active': r.get('active', True),
            }
            new_raw = dump_json(new_vals)

            st, tmid = self._target_model_state(ctx, tname)
            existing = None
            if st == 'real':
                res = ctx['target_rpc'].search_read(
                    'ir.rule', [('model_id', '=', tmid), ('name', '=', r['name'])],
                    ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'], limit=1,
                )
                if res:
                    existing = res[0]

            if not existing:
                changes.append({
                    'object_type': 'record_rule',
                    'change_type': 'create',
                    'name': f"rule {r['name']}",
                    'target_ref': tname,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Create record rule"),
                })
            else:
                tgt_gids = existing.get('groups') or []
                tgt_grefs = sorted([self._get_xml_id(ctx['target_rpc'], 'res.groups', gid, ctx['cache']) or f"id:{gid}" for gid in tgt_gids])
                old_vals = {
                    'name': existing['name'],
                    'model': tname,
                    'domain_force': existing.get('domain_force') or '',
                    'groups': tgt_grefs,
                    'perm_read': existing.get('perm_read', False),
                    'perm_write': existing.get('perm_write', False),
                    'perm_create': existing.get('perm_create', False),
                    'perm_unlink': existing.get('perm_unlink', False),
                    'active': existing.get('active', True),
                }
                old_raw = dump_json(old_vals)
                if same(old_vals, new_vals, ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active']):
                    change_type = 'unchanged'
                    msg = _("Record rule in sync.")
                else:
                    change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
                    msg = _("Record rule differs.")

                changes.append({
                    'object_type': 'record_rule',
                    'change_type': change_type,
                    'name': f"rule {r['name']}",
                    'target_ref': tname,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'message': msg,
                })

        return changes
