import ast
import logging
from odoo import api, models, _
from odoo.exceptions import UserError

from .rpc_helper import OdooRPCError
from .diff_utils import dump_json, norm, same, dump_server_action, build_xml_id, replace_action_references_in_arch
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

        job = self.job_id
        target_mod = (job.target_module_name or 'meta_migrator').strip() if job else 'meta_migrator'

        # Pre-scan model steps and field steps across the whole job for dependency & ordering analysis
        model_step_info = {}
        field_step_info = {}
        model_all_fields_step_info = {}
        pre_scanned_fields = set()

        for idx, step in enumerate(steps):
            otype = step.get('object_type')
            act = step.get('action')
            seq = step.get('sequence', 10)
            if otype == 'model' and act == 'create':
                src_m = step.get('model_name')
                if src_m:
                    tgt_m = rename_map.get(src_m, src_m)
                    if tgt_m not in model_step_info:
                        model_step_info[tgt_m] = {
                            'step_i': idx,
                            'sequence': seq,
                            'step': step,
                        }
            elif otype == 'field':
                m = step.get('model_name')
                fname = step.get('field_name')
                if m:
                    tmodel = rename_map.get(m, m)
                    if fname:
                        pre_scanned_fields.add((tmodel, fname))
                        if (tmodel, fname) not in field_step_info:
                            field_step_info[(tmodel, fname)] = {
                                'step_i': idx,
                                'sequence': seq,
                                'step': step,
                            }
                    else:
                        if tmodel not in model_all_fields_step_info:
                            model_all_fields_step_info[tmodel] = {
                                'step_i': idx,
                                'sequence': seq,
                                'step': step,
                            }

        return {
            'source_rpc': source_rpc,
            'target_rpc': target_rpc,
            'cache': cache,
            'rename_map': rename_map,
            'dry_run': self.mode == 'test',
            'planned_models': set(),
            'planned_fields': set(),
            'planned_xml_ids': set(),
            'target_module': target_mod,
            'job': job,
            'steps': steps,
            'all_steps': steps,
            'model_step_info': model_step_info,
            'field_step_info': field_step_info,
            'model_all_fields_step_info': model_all_fields_step_info,
            'pre_scanned_fields': pre_scanned_fields,
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
            changes = [{
                'object_type': 'model',
                'change_type': 'create',
                'name': f"model {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': new_raw,
                'extra_raw': extra_raw,
                'message': _("Create custom model %s") % tname,
            }]
        else:
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
            changes = [{
                'object_type': 'model',
                'change_type': change_type,
                'name': f"model {tname}",
                'target_ref': tname,
                'old_raw': old_raw,
                'new_raw': new_raw,
                'extra_raw': extra_raw,
                'message': msg,
            }]

        # Check fields of this model on source if not explicitly listed in separate field steps:
        steps_list = ctx.get('steps') or []
        has_explicit_field_steps = any(
            s.get('object_type') == 'field' and ctx['rename_map'].get(s.get('model_name'), s.get('model_name')) == tname
            for s in steps_list
        )
        has_explicit_view_steps = any(
            s.get('object_type') == 'view' and ctx['rename_map'].get(s.get('model_name'), s.get('model_name')) == tname
            for s in steps_list
        )
        has_explicit_access_steps = any(
            s.get('object_type') == 'access_right' and ctx['rename_map'].get(s.get('model_name'), s.get('model_name')) == tname
            for s in steps_list
        )
        has_explicit_rule_steps = any(
            s.get('object_type') == 'record_rule' and ctx['rename_map'].get(s.get('model_name'), s.get('model_name')) == tname
            for s in steps_list
        )
        has_explicit_menu_steps = any(
            s.get('object_type') == 'menu' and ctx['rename_map'].get(s.get('model_name'), s.get('model_name')) == tname
            for s in steps_list
        )

        if not has_explicit_field_steps:
            source_fields = src.search_read(
                'ir.model.fields',
                [('model', '=', m), ('state', '=', 'manual')],
                ALL_FIELD_KEYS,
            )
            if source_fields:
                items = []
                for fvals in source_fields:
                    items.append({
                        'model_name': m,
                        'tmodel': tname,
                        'fvals': fvals,
                    })
                declared = {(it['tmodel'], it['fvals']['name']) for it in items}
                for it in items:
                    f_change = self._plan_one_field(it, ctx)
                    rel_err = self._check_relations(it, declared, ctx)
                    if rel_err:
                        f_change['change_type'] = 'error'
                        f_change['message'] = (f_change['message'] + ' | ' if f_change.get('message') else '') + rel_err
                    changes.append(f_change)

        # Related Options (Auto-create on target)
        if step.get('create_list_view') and not has_explicit_view_steps:
            changes.extend(self._plan_views_for_model_by_type(m, tname, ctx, 'list'))
        if step.get('create_form_view') and not has_explicit_view_steps:
            changes.extend(self._plan_views_for_model_by_type(m, tname, ctx, 'form'))
        if step.get('create_search_view') and not has_explicit_view_steps:
            changes.extend(self._plan_views_for_model_by_type(m, tname, ctx, 'search'))
        if step.get('copy_access_rights') and not has_explicit_access_steps:
            changes.extend(self._plan_access_rights_for_model({'model_name': m}, ctx))
        if step.get('copy_record_rules') and not has_explicit_rule_steps:
            changes.extend(self._plan_record_rules_for_model({'model_name': m}, ctx))
        if step.get('create_menu') and not has_explicit_menu_steps:
            changes.extend(self._plan_menus_for_model({'model_name': m}, ctx))

        return changes

    def _plan_views_for_model_by_type(self, m, tname, ctx, vtype):
        res = self._plan_view_create({'model_name': m, 'view_type': vtype}, ctx)
        return [c for c in res if c.get('change_type') != 'unchanged' or not c.get('message', '').startswith("No views found")]

    def _plan_field_block(self, block, base_index, ctx):
        items = []
        out = {}
        for offset, step in enumerate(block):
            step_i = base_index + offset
            m = step.get('model_name')
            fname = step.get('field_name')
            xml_id = step.get('xml_id')
            tmodel = ctx['rename_map'].get(m, m) if m else ''

            if xml_id:
                if '.' not in xml_id:
                    items.append({
                        'step_i': step_i,
                        'model_name': m or '',
                        'tmodel': tmodel or '',
                        'fvals': None,
                        'missing_fname': xml_id,
                        'err_msg': _("Invalid XML ID '%s'. Use module.name format.") % xml_id,
                    })
                    continue
                module, name = xml_id.split('.', 1)
                src_data = ctx['source_rpc'].search_read(
                    'ir.model.data',
                    [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.model.fields')],
                    ['res_id', 'model'], limit=1,
                )
                if not src_data:
                    items.append({
                        'step_i': step_i,
                        'model_name': m or '',
                        'tmodel': tmodel or '',
                        'fvals': None,
                        'missing_fname': xml_id,
                        'err_msg': _("Field with XML ID '%s' was not found on source.") % xml_id,
                    })
                else:
                    fields_data = ctx['source_rpc'].read('ir.model.fields', [src_data[0]['res_id']], ALL_FIELD_KEYS)
                    if not fields_data:
                        items.append({
                            'step_i': step_i,
                            'model_name': m or '',
                            'tmodel': tmodel or '',
                            'fvals': None,
                            'missing_fname': xml_id,
                            'err_msg': _("Field record for XML ID '%s' was not found on source.") % xml_id,
                        })
                    else:
                        fvals = fields_data[0]
                        field_m = fvals.get('model') or m
                        field_tmodel = ctx['rename_map'].get(field_m, field_m)
                        items.append({
                            'step_i': step_i,
                            'model_name': field_m,
                            'tmodel': field_tmodel,
                            'fvals': fvals,
                            'xml_id': xml_id,
                        })
            elif step.get('ttype'):
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
                v_errors = self._validate_virtual_field(fvals)
                if v_errors:
                    for err in v_errors:
                        err_change = {
                            'object_type': 'field',
                            'change_type': 'error',
                            'name': f"field {tmodel}.{fname}" if fname else f"field on {tmodel}",
                            'target_ref': f"{tmodel}.{fname}" if fname else tmodel,
                            'old_raw': '',
                            'new_raw': dump_json(fvals),
                            'message': err,
                        }
                        out.setdefault(step_i, []).append(err_change)
                    continue

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
                elif not fname and not fields_data:
                    items.append({
                        'step_i': step_i,
                        'model_name': m,
                        'tmodel': tmodel,
                        'fvals': None,
                        'no_manual_fields': True,
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

        for it in items:
            if it.get('no_manual_fields'):
                unchanged_change = {
                    'object_type': 'field',
                    'change_type': 'unchanged',
                    'name': f"manual fields for {it['tmodel']}",
                    'target_ref': it['tmodel'],
                    'old_raw': '',
                    'new_raw': '',
                    'message': _("No manual fields found on source for model '%s'.") % it['model_name'],
                }
                out.setdefault(it['step_i'], []).append(unchanged_change)
                continue

            if not it.get('fvals'):
                err_msg = it.get('err_msg') or (_("Field '%s.%s' not found on source or state != manual.") % (it['model_name'], it.get('missing_fname', '')))
                target_ref = it.get('missing_fname', '') if '.' in it.get('missing_fname', '') else f"{it['tmodel']}.{it.get('missing_fname', '')}"
                err_change = {
                    'object_type': 'field',
                    'change_type': 'error',
                    'name': f"field {target_ref}",
                    'target_ref': target_ref,
                    'old_raw': '',
                    'new_raw': '',
                    'message': err_msg,
                }
                out.setdefault(it['step_i'], []).append(err_change)
                continue

            change = self._plan_one_field(it, ctx)
            if it.get('xml_id'):
                change['target_ref'] = it['xml_id']
            err = self._check_relations(it, declared, ctx)
            if err:
                change['change_type'] = 'error'
                change['message'] = (change['message'] + ' | ' if change.get('message') else '') + err
            out.setdefault(it['step_i'], []).append(change)

        return out

    def _validate_virtual_field(self, fvals):
        """Structural validation of virtual field values. Returns list of error strings."""
        errors = []
        fname = (fvals.get('name') or '').strip()
        ttype = (fvals.get('ttype') or '').strip()
        compute = fvals.get('compute')
        depends = fvals.get('depends')
        related = fvals.get('related')
        relation = fvals.get('relation')
        rel_field = fvals.get('relation_field')
        selection = fvals.get('selection')

        # 1. Field name
        if not fname:
            errors.append(_("Field name is required."))
        elif not fname.isidentifier():
            errors.append(_("Field name '%s' is not a valid Python identifier.") % fname)
        elif not fname.startswith('x_'):
            errors.append(_("Custom field '%s' must begin with 'x_'.") % fname)

        # 2. Field type
        valid_types = {
            'char', 'text', 'html', 'integer', 'float', 'monetary',
            'boolean', 'date', 'datetime', 'selection',
            'many2one', 'one2many', 'many2many', 'binary',
        }
        if not ttype:
            errors.append(_("Field type (ttype) is required."))
        elif ttype not in valid_types:
            errors.append(_("Field '%s': unknown field type '%s'.") % (fname, ttype))

        # 3. Relational fields require relation
        if ttype in ('many2one', 'one2many', 'many2many') and not relation:
            errors.append(_("Field '%s' (%s): 'relation' (target model name) is required.") % (fname, ttype))

        # 4. One2many requires relation_field
        if ttype == 'one2many' and not rel_field:
            errors.append(_("One2many field '%s': 'relation_field' (inverse field name on '%s') is required.") % (fname, relation or 'related model'))

        # 5. Many2many should not specify relation_field
        if ttype == 'many2many' and rel_field:
            errors.append(_("Many2many field '%s': 'relation_field' is not applicable for many2many.") % fname)

        # 6. Selection requires options
        if ttype == 'selection':
            if not selection:
                errors.append(_("Selection field '%s': 'selection' options list is required (e.g. \"[('draft', 'Draft'), ('done', 'Done')]\").") % fname)
            elif isinstance(selection, str):
                try:
                    parsed = ast.literal_eval(selection)
                    if not isinstance(parsed, (list, tuple)):
                        errors.append(_("Selection field '%s': selection must be a list of (key, label) tuples.") % fname)
                except Exception as e:
                    errors.append(_("Selection field '%s': invalid selection syntax: %s") % (fname, e))

        # 7. Compute & Depends
        if compute and not depends:
            errors.append(_("Field '%s': 'compute' is defined but 'depends' is missing. Add 'depends' (comma-separated field names).") % fname)
        if depends and not compute:
            errors.append(_("Field '%s': 'depends' is defined but 'compute' is missing.") % fname)

        # 8. Related
        if related and compute:
            errors.append(_("Field '%s': 'related' and 'compute' are mutually exclusive.") % fname)
        if related and depends:
            errors.append(_("Field '%s': 'related' and 'depends' are mutually exclusive.") % fname)
        if related and '.' not in related:
            errors.append(_("Related field '%s': 'related' must be a dot-separated field path (e.g. 'partner_id.name').") % fname)

        return errors

    def _check_field_order(self, it, rel_target, rel_field, ctx):
        """
        Check that the dependent field (rel_target, rel_field) is scheduled to be
        created BEFORE this field. Uses sequence and step index to compare.
        """
        fname = it['fvals'].get('name') or it['fvals'].get('field_name') or ''
        tmodel = it['tmodel']
        step_i = it.get('step_i', 0)
        steps = ctx.get('steps', [])
        current_step = steps[step_i] if step_i < len(steps) else {}
        current_seq = current_step.get('sequence', 10)

        field_info = ctx.get('field_step_info', {}).get((rel_target, rel_field))
        all_fields_info = ctx.get('model_all_fields_step_info', {}).get(rel_target)
        dep_info = field_info or all_fields_info

        if dep_info:
            dep_i = dep_info['step_i']
            dep_seq = dep_info['sequence']
            if dep_seq >= current_seq:
                return _(
                    "One2many '%s.%s' (seq %d) requires '%s.%s' to be created first, "
                    "but that field is planned in step %d (seq %d) which runs later or at the same time. "
                    "Move the many2one step to a lower sequence number."
                ) % (tmodel, fname, current_seq, rel_target, rel_field, dep_i + 1, dep_seq)

            dep_step = dep_info.get('step', {})
            if dep_step.get('relation'):
                dep_rel = ctx['rename_map'].get(dep_step['relation'], dep_step['relation'])
                if dep_rel != tmodel:
                    return _("One2many '%s.%s': relation_field '%s.%s' points to '%s', expected '%s'.") % (
                        tmodel, fname, rel_target, rel_field, dep_rel, tmodel,
                    )
            return None

        return _(
            "Relation field '%s' for one2many '%s.%s' does not exist on model '%s' and has no step planned to create it. "
            "Add a step to create field '%s' on '%s' before this step."
        ) % (rel_field, tmodel, fname, rel_target, rel_field, rel_target)

    def _check_related_chain(self, it, related, declared, ctx):
        """Validates that the first field segment in a related expression exists or is planned."""
        tmodel = it['tmodel']
        fname = it['fvals'].get('name') or ''
        parts = related.strip().split('.')
        if len(parts) < 2:
            return None

        first_field = parts[0]
        if (tmodel, first_field) in declared:
            return None

        if (tmodel, first_field) in ctx.get('pre_scanned_fields', set()):
            f_info = ctx.get('field_step_info', {}).get((tmodel, first_field))
            if f_info:
                step_i = it.get('step_i', 0)
                current_seq = ctx.get('steps', [])[step_i].get('sequence', 10) if step_i < len(ctx.get('steps', [])) else 10
                if f_info['step_i'] > step_i or f_info['sequence'] >= current_seq:
                    return _(
                        "Related field '%s.%s': first segment '%s' is planned in step %d (seq %d) "
                        "which runs later or at the same time. Move that field step before this one."
                    ) % (tmodel, fname, first_field, f_info['step_i'] + 1, f_info['sequence'])
            return None

        st, tmid = self._target_model_state(ctx, tmodel)
        if st == 'real' and tmid:
            existing = ctx['target_rpc'].search_read(
                'ir.model.fields',
                [('model_id', '=', tmid), ('name', '=', first_field)],
                ['id'], limit=1,
            )
            if existing:
                return None

        return _(
            "Related field '%s.%s': first segment '%s' does not exist on model '%s' "
            "and no step is planned to create it."
        ) % (tmodel, fname, first_field, tmodel)

    def _check_relations(self, it, declared, ctx):
        fvals = it['fvals']
        ttype = fvals.get('ttype')
        rename_map = ctx['rename_map']
        tmodel = it['tmodel']
        fname = fvals.get('name') or fvals.get('field_name') or ''
        step_i = it.get('step_i', 0)
        steps = ctx.get('steps', [])
        current_step = steps[step_i] if step_i < len(steps) else {}
        current_seq = current_step.get('sequence', 10)

        # 1. Check owner model existence and execution order
        st_owner, _owner_mid = self._target_model_state(ctx, tmodel)
        if not st_owner:
            owner_step_info = ctx.get('model_step_info', {}).get(tmodel)
            if owner_step_info:
                if owner_step_info['sequence'] >= current_seq:
                    return _(
                        "Model '%s' does not exist on target yet and its 'create model' step (step %d, seq %d) "
                        "runs after or at the same time as field '%s.%s' (step %d, seq %d). "
                        "Move the 'create model' step before this field."
                    ) % (tmodel, owner_step_info['step_i'] + 1, owner_step_info['sequence'], tmodel, fname, step_i + 1, current_seq)
            else:
                return _("Target model '%s' does not exist on target and has no preceding 'create model' step.") % tmodel

        # 2. Check relational model existence and execution order
        if ttype in ('many2one', 'one2many', 'many2many') and fvals.get('relation'):
            rel_source = fvals['relation']
            rel_target = rename_map.get(rel_source, rel_source)
            st_rel, _target_mid = self._target_model_state(ctx, rel_target)
            if not st_rel:
                rel_step_info = ctx.get('model_step_info', {}).get(rel_target)
                if rel_step_info:
                    if rel_step_info['sequence'] >= current_seq:
                        return _(
                            "Relational model '%s' does not exist on target yet and its 'create model' step (step %d, seq %d) "
                            "runs after or at the same time as field '%s.%s' (step %d, seq %d). "
                            "Move the 'create model' step before this field."
                        ) % (rel_target, rel_step_info['step_i'] + 1, rel_step_info['sequence'], tmodel, fname, step_i + 1, current_seq)
                else:
                    return _("Target relational model '%s' does not exist on target and has no preceding create step.") % rel_target

        # 3. Check one2many relation_field existence, order, and type
        if ttype == 'one2many':
            rel_source = fvals.get('relation')
            rel_target = rename_map.get(rel_source, rel_source)
            rel_field = fvals.get('relation_field')
            if not rel_field:
                return _("One2many field '%s' is missing relation_field.") % fname

            field_exists_on_tgt = False
            st_rel, tmid = self._target_model_state(ctx, rel_target)
            if st_rel == 'real' and tmid:
                existing = ctx['target_rpc'].search_read(
                    'ir.model.fields',
                    [('model_id', '=', tmid), ('name', '=', rel_field)],
                    ['id', 'ttype', 'relation'], limit=1,
                )
                if existing:
                    field_exists_on_tgt = True
                    rf_type = existing[0].get('ttype')
                    rf_rel = existing[0].get('relation')
                    if rf_type not in ('many2one', 'many2many'):
                        return _("One2many '%s.%s': relation_field '%s.%s' exists on target but is type '%s', expected many2one.") % (
                            tmodel, fname, rel_target, rel_field, rf_type,
                        )
                    if rf_rel and rf_rel != tmodel:
                        return _("One2many '%s.%s': relation_field '%s.%s' points to '%s', expected '%s'.") % (
                            tmodel, fname, rel_target, rel_field, rf_rel, tmodel,
                        )

            if not field_exists_on_tgt:
                # If in declared (same field block), executor pass1 handles non-o2m first
                if (rel_target, rel_field) in declared:
                    pass
                else:
                    err = self._check_field_order(it, rel_target, rel_field, ctx)
                    if err:
                        return err

        # 4. Check related field chain
        related = fvals.get('related')
        if related:
            err = self._check_related_chain(it, related, declared, ctx)
            if err:
                return err

        # 5. Check computed field logic
        compute = fvals.get('compute')
        depends = fvals.get('depends')
        if compute and not depends:
            return _("Computed field '%s.%s': 'compute' is set but 'depends' is missing.") % (tmodel, fname)
        if depends and not compute:
            return _("Field '%s.%s': 'depends' is set but 'compute' is missing.") % (tmodel, fname)

        return None

    def _plan_one_field(self, it, ctx):
        fvals = it['fvals']
        tmodel = it['tmodel']
        fname = fvals['name']
        target_mod = ctx.get('target_module') or 'meta_migrator'
        target_xml_id = it.get('xml_id') or build_xml_id(target_mod, 'field', fname, model_name=tmodel)
        target_ref = it.get('xml_id') or f"{tmodel}.{fname}"
        new_vals = self._build_field_vals(fvals, ctx['rename_map'])
        for k in FIELD_LOGIC_KEYS:
            if fvals.get(k):
                new_vals[k] = fvals[k]

        new_raw = dump_json(new_vals)
        st, tmid = self._target_model_state(ctx, tmodel)

        tgt_field = None
        if '.' in target_xml_id:
            tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
            tgt_data = ctx['target_rpc'].search_read(
                'ir.model.data',
                [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.model.fields')],
                ['res_id'], limit=1,
            )
            if tgt_data:
                tgt_recs = ctx['target_rpc'].read('ir.model.fields', [tgt_data[0]['res_id']], list(new_vals.keys()))
                if tgt_recs:
                    tgt_field = tgt_recs[0]

        if not tgt_field and st == 'real':
            existing = ctx['target_rpc'].search_read(
                'ir.model.fields',
                [('model_id', '=', tmid), ('name', '=', fname)],
                list(new_vals.keys()), limit=1,
            )
            if existing:
                tgt_field = existing[0]

        if not tgt_field:
            if (tmodel, fname) in ctx['planned_fields']:
                return {
                    'object_type': 'field',
                    'change_type': 'unchanged',
                    'name': f"field {tmodel}.{fname}",
                    'target_ref': target_ref,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Field already planned in preceding step."),
                }
            ctx['planned_fields'].add((tmodel, fname))
            return {
                'object_type': 'field',
                'change_type': 'create',
                'name': f"field {tmodel}.{fname}",
                'target_ref': target_ref,
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
            'target_ref': target_ref,
            'old_raw': old_raw,
            'new_raw': new_raw,
            'message': msg,
        }

    def _plan_view(self, step, ctx):
        if step.get('action') == 'update' and step.get('arch'):
            return self._plan_view_update(step, ctx)
        return self._plan_view_create(step, ctx)

    def _plan_view_create(self, step, ctx):
        if step.get('xml_id'):
            return self._plan_view_by_xml_id(step, ctx)

        m = step.get('model_name')
        tname = ctx['rename_map'].get(m, m)
        vtype = step.get('view_type')

        st, _tmid = self._target_model_state(ctx, tname)
        if not st:
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"views on {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("Target model '%s' does not exist and has no preceding create step.") % tname,
            }]

        if step.get('arch'):
            vtype = vtype or 'form'
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

        domain = [('model', '=', m), ('active', '=', True)]
        if vtype:
            search_types = [vtype] if vtype != 'list' else ['list', 'tree']
            domain.append(('type', 'in', search_types))

        views = ctx['source_rpc'].search_read(
            'ir.ui.view',
            domain,
            ['id', 'name', 'type', 'arch', 'priority', 'inherit_id', 'mode'],
        )
        if not views:
            return [{
                'object_type': 'view',
                'change_type': 'unchanged',
                'name': f"views for {m}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("No views found on source for model '%s'.") % m,
            }]

        views.sort(key=lambda v: v.get('priority', 16))
        changes = []
        target_mod = ctx.get('target_module') or 'meta_migrator'
        for view in views:
            v_t = view.get('type') or 'form'
            src_data = ctx['source_rpc'].search_read(
                'ir.model.data',
                [('model', '=', 'ir.ui.view'), ('res_id', '=', view['id'])],
                ['module', 'name'], limit=1,
            )
            src_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}" if (src_data and src_data[0].get('module') and src_data[0].get('name')) else False
            target_xml_id = src_xml_id or build_xml_id(target_mod, 'view', view['name'], model_name=tname)
            target_ref = target_xml_id

            raw_arch = (view.get('arch') or '').strip()
            new_raw = replace_action_references_in_arch(raw_arch, ctx['source_rpc'], ctx['target_rpc'], target_mod, ctx['cache'])
            v_extra = dump_json({
                'name': view.get('name') or f"{v_t} view on {tname}",
                'type': v_t,
                'model': tname,
                'priority': view.get('priority', 16),
                'inherit_name': (view.get('inherit_id') or [None, None])[1] if isinstance(view.get('inherit_id'), (list, tuple)) else False,
                'xml_id': target_xml_id,
            })

            tgt_view = None
            if '.' in target_xml_id:
                tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
                tgt_data = ctx['target_rpc'].search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.ui.view')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    tgt_recs = ctx['target_rpc'].read('ir.ui.view', [tgt_data[0]['res_id']], ['id', 'arch', 'name', 'type'])
                    if tgt_recs:
                        tgt_view = tgt_recs[0]
            if not tgt_view:
                existing = ctx['target_rpc'].search_read(
                    'ir.ui.view',
                    [('model', '=', tname), ('type', '=', v_t), ('name', '=', view['name'])],
                    ['id', 'arch', 'name', 'type'], limit=1,
                )
                if existing:
                    tgt_view = existing[0]

            if not tgt_view:
                changes.append({
                    'object_type': 'view',
                    'change_type': 'create',
                    'name': f"view {v_t} '{view['name']}' on {tname}",
                    'target_ref': target_ref,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'extra_raw': v_extra,
                    'message': _("Create new %s view '%s' for %s") % (v_t, view['name'], tname),
                })
            else:
                old_raw = (tgt_view.get('arch') or '').strip()
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
                changes.append({
                    'object_type': 'view',
                    'change_type': change_type,
                    'name': f"view {v_t} '{view['name']}' on {tname}",
                    'target_ref': target_ref,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'extra_raw': v_extra,
                    'message': msg,
                })

        return changes

    def _plan_view_by_xml_id(self, step, ctx):
        xml_id = step['xml_id']
        if '.' not in xml_id:
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"view {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Invalid XML ID '%s'. Use module.name format.") % xml_id,
            }]
        module, name = xml_id.split('.', 1)
        src_data = ctx['source_rpc'].search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name)],
            ['res_id', 'model'], limit=1,
        )
        if not src_data or src_data[0]['model'] != 'ir.ui.view':
            return [{
                'object_type': 'view',
                'change_type': 'error',
                'name': f"view {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("View with XML ID '%s' was not found on source.") % xml_id,
            }]

        view = ctx['source_rpc'].read(
            'ir.ui.view', [src_data[0]['res_id']],
            ['id', 'name', 'type', 'arch', 'priority', 'inherit_id', 'mode', 'model'],
        )[0]
        m = view.get('model') or step.get('model_name') or ''
        tname = ctx['rename_map'].get(m, m)
        v_t = view.get('type') or 'form'
        v_name = view.get('name') or step.get('view_name') or xml_id
        target_mod = ctx.get('target_module') or module
        raw_arch = (view.get('arch') or '').strip()
        new_raw = replace_action_references_in_arch(raw_arch, ctx['source_rpc'], ctx['target_rpc'], target_mod, ctx['cache'])
        v_extra = dump_json({
            'name': v_name,
            'type': v_t,
            'model': tname,
            'priority': view.get('priority', 16),
            'inherit_name': (view.get('inherit_id') or [None, None])[1] if isinstance(view.get('inherit_id'), (list, tuple)) else False,
            'xml_id': xml_id,
        })

        tgt_data = ctx['target_rpc'].search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.ui.view')],
            ['res_id'], limit=1,
        )
        tgt_view = None
        if tgt_data:
            tgt_recs = ctx['target_rpc'].read('ir.ui.view', [tgt_data[0]['res_id']], ['id', 'arch', 'name', 'type'])
            if tgt_recs:
                tgt_view = tgt_recs[0]
        if not tgt_view and tname:
            existing = ctx['target_rpc'].search_read(
                'ir.ui.view',
                [('model', '=', tname), ('type', '=', v_t), ('name', '=', v_name)],
                ['id', 'arch', 'name', 'type'], limit=1,
            )
            if existing:
                tgt_view = existing[0]

        if not tgt_view:
            return [{
                'object_type': 'view',
                'change_type': 'create',
                'name': f"view {v_t} '{v_name}' on {tname or xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': new_raw,
                'extra_raw': v_extra,
                'message': _("Create view %s (%s)") % (v_name, xml_id),
            }]

        old_raw = (tgt_view.get('arch') or '').strip()
        if view_merge.canonical_text(new_raw) == view_merge.canonical_text(old_raw):
            change_type = 'unchanged'
            msg = _("View matches target exactly.")
        else:
            if self.on_conflict == 'overwrite' or step.get('action') == 'update':
                change_type = 'update'
                msg = _("View arch differs; will overwrite.")
            else:
                change_type = 'exists'
                msg = _("View arch differs; skipped due to conflict policy.")

        return [{
            'object_type': 'view',
            'change_type': change_type,
            'name': f"view {v_t} '{v_name}' on {tname or xml_id}",
            'target_ref': xml_id,
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
        if step.get('xml_id'):
            return self._plan_server_action_by_xml_id(step, ctx)
        return self._plan_server_actions_for_model(step, ctx)

    def _plan_server_action_by_xml_id(self, step, ctx):
        xml_id = step['xml_id']
        if '.' not in xml_id:
            return [{
                'object_type': 'server_action',
                'change_type': 'error',
                'name': f"server action {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Invalid XML ID '%s'. Use module.name format.") % xml_id,
            }]
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

    def _plan_server_actions_for_model(self, step, ctx):
        m = step.get('model_name')
        tname = ctx['rename_map'].get(m, m)
        src_models = ctx['source_rpc'].search_read('ir.model', [('model', '=', m)], ['id'], limit=1)
        if not src_models:
            return [{
                'object_type': 'server_action',
                'change_type': 'error',
                'name': f"server actions for {m}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("Model '%s' was not found on source.") % m,
            }]

        src_mid = src_models[0]['id']
        actions = ctx['source_rpc'].search_read(
            'ir.actions.server',
            ['|', ('model_id', '=', src_mid), ('binding_model_id', '=', src_mid)],
            ['id', 'name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'],
        )
        if not actions:
            return [{
                'object_type': 'server_action',
                'change_type': 'unchanged',
                'name': f"server actions for {m}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("No server actions found on source for model '%s'.") % m,
            }]

        changes = []
        target_mod = ctx.get('target_module') or 'meta_migrator'
        for action in actions:
            src_data = ctx['source_rpc'].search_read(
                'ir.model.data',
                [('model', '=', 'ir.actions.server'), ('res_id', '=', action['id'])],
                ['module', 'name'], limit=1,
            )
            act_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}" if (src_data and src_data[0].get('module') and src_data[0].get('name')) else False
            target_xml_id = act_xml_id or build_xml_id(target_mod, 'server_action', action['name'])
            target_ref = target_xml_id

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

            tgt_action = None
            if '.' in target_xml_id:
                tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
                tgt_data = ctx['target_rpc'].search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.actions.server')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    tgt_recs = ctx['target_rpc'].read(
                        'ir.actions.server', [tgt_data[0]['res_id']],
                        ['name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'],
                    )
                    if tgt_recs:
                        tgt_action = tgt_recs[0]
            if not tgt_action:
                tgt_mid = False
                if tgt_m:
                    tms = ctx['target_rpc'].search_read('ir.model', [('model', '=', tgt_m)], ['id'], limit=1)
                    if tms:
                        tgt_mid = tms[0]['id']
                dom = [('name', '=', action['name'])]
                if tgt_mid:
                    dom.append(('model_id', '=', tgt_mid))
                existing = ctx['target_rpc'].search_read(
                    'ir.actions.server', dom,
                    ['name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'], limit=1,
                )
                if existing:
                    tgt_action = existing[0]

            if not tgt_action:
                changes.append({
                    'object_type': 'server_action',
                    'change_type': 'create',
                    'name': f"server action '{action['name']}'",
                    'target_ref': target_ref,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Create server action '%s'") % action['name'],
                })
            else:
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
                    if self.on_conflict == 'overwrite':
                        change_type = 'update'
                        msg = _("Server action differs; will overwrite.")
                    else:
                        change_type = 'exists'
                        msg = _("Server action differs; skipped due to conflict policy.")
                changes.append({
                    'object_type': 'server_action',
                    'change_type': change_type,
                    'name': f"server action '{action['name']}'",
                    'target_ref': target_ref,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'message': msg,
                })

        return changes

    def _plan_menu(self, step, ctx):
        if step.get('xml_id'):
            return self._plan_menu_by_xml_id(step, ctx)
        return self._plan_menus_for_model(step, ctx)

    def _plan_menu_by_xml_id(self, step, ctx):
        xml_id = step['xml_id']
        if '.' not in xml_id:
            return [{
                'object_type': 'menu',
                'change_type': 'error',
                'name': f"menu {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Invalid XML ID '%s'. Use module.name format.") % xml_id,
            }]
        module, name = xml_id.split('.', 1)
        src_data = ctx['source_rpc'].search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name)],
            ['res_id', 'model'], limit=1,
        )
        if not src_data or src_data[0]['model'] not in ('ir.ui.menu', 'ir.actions.act_window'):
            return [{
                'object_type': 'menu',
                'change_type': 'error',
                'name': f"menu {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Menu or window action with XML ID '%s' not found on source.") % xml_id,
            }]

        m = step.get('model_name') or ''
        tname = ctx['rename_map'].get(m, m) if m else ''

        if src_data[0]['model'] == 'ir.ui.menu':
            m_items = ctx['source_rpc'].read(
                'ir.ui.menu', [src_data[0]['res_id']],
                ['id', 'name', 'parent_id', 'sequence', 'active', 'web_icon', 'action'],
            )
            if not m_items:
                return []
            m_item = m_items[0]
            changes = []
            if m_item.get('action') and isinstance(m_item['action'], str) and m_item['action'].startswith('ir.actions.act_window,'):
                act_id = int(m_item['action'].split(',')[1])
                src_acts = ctx['source_rpc'].read(
                    'ir.actions.act_window', [act_id],
                    ['id', 'name', 'res_model', 'view_mode', 'domain', 'context', 'limit', 'target'],
                )
                if src_acts:
                    act_m = src_acts[0]['res_model']
                    act_tname = ctx['rename_map'].get(act_m, act_m)
                    changes.extend(self._plan_one_window_action(src_acts[0], act_tname, ctx))
            changes.append(self._plan_one_menu_item(m_item, tname, ctx, xml_id=xml_id))
            return changes
        else:
            # ir.actions.act_window
            src_acts = ctx['source_rpc'].read(
                'ir.actions.act_window', [src_data[0]['res_id']],
                ['id', 'name', 'res_model', 'view_mode', 'domain', 'context', 'limit', 'target'],
            )
            if not src_acts:
                return []
            act_m = src_acts[0]['res_model']
            act_tname = ctx['rename_map'].get(act_m, act_m)
            return self._plan_window_action_and_menus(src_acts[0], act_tname, ctx)

    def _plan_one_window_action(self, src_act, tname, ctx):
        target_mod = ctx.get('target_module') or 'meta_migrator'
        target_xml_id = build_xml_id(target_mod, 'action', src_act['name'], model_name=tname)
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
        existing_act = None
        if '.' in target_xml_id:
            tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
            tgt_data = ctx['target_rpc'].search_read(
                'ir.model.data',
                [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.actions.act_window')],
                ['res_id'], limit=1,
            )
            if tgt_data:
                tgt_recs = ctx['target_rpc'].read('ir.actions.act_window', [tgt_data[0]['res_id']], list(act_vals.keys()))
                if tgt_recs:
                    existing_act = tgt_recs
        if not existing_act:
            existing_act = ctx['target_rpc'].search_read(
                'ir.actions.act_window', [('name', '=', src_act['name']), ('res_model', '=', tname)],
                list(act_vals.keys()), limit=1,
            )
        if not existing_act:
            return [{
                'object_type': 'menu',
                'change_type': 'create',
                'name': f"window action: {src_act['name']}",
                'target_ref': target_xml_id,
                'old_raw': '',
                'new_raw': new_act_raw,
                'message': _("Create window action '%s'") % src_act['name'],
            }]
        old_act_dict = {k: existing_act[0].get(k) for k in act_vals}
        old_act_raw = dump_json(old_act_dict)
        if same(old_act_dict, act_vals, list(act_vals.keys())):
            act_change_type = 'unchanged'
            act_msg = _("Window action in sync.")
        else:
            act_change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
            act_msg = _("Window action differs.")
        return [{
            'object_type': 'menu',
            'change_type': act_change_type,
            'name': f"window action: {src_act['name']}",
            'target_ref': target_xml_id,
            'old_raw': old_act_raw,
            'new_raw': new_act_raw,
            'message': act_msg,
        }]

    def _plan_one_menu_item(self, m_item, tname, ctx, xml_id=None):
        target_mod = ctx.get('target_module') or 'meta_migrator'
        target_xml_id = xml_id or build_xml_id(target_mod, 'menu', m_item['name'])
        m_vals = {
            'name': m_item['name'],
            'sequence': m_item.get('sequence', 10),
            'active': m_item.get('active', True),
            'action': f"ir.actions.act_window for {tname}" if tname else '',
        }
        new_m_raw = dump_json(m_vals)
        tgt_m_recs = None
        if '.' in target_xml_id:
            tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
            tgt_data = ctx['target_rpc'].search_read(
                'ir.model.data',
                [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.ui.menu')],
                ['res_id'], limit=1,
            )
            if tgt_data:
                tgt_recs = ctx['target_rpc'].read('ir.ui.menu', [tgt_data[0]['res_id']], ['id', 'name', 'sequence', 'active'])
                if tgt_recs:
                    tgt_m_recs = tgt_recs
        if not tgt_m_recs:
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
                'action': f"ir.actions.act_window for {tname}" if tname else '',
            }
            m_old_raw = dump_json(old_m_dict)
            if same(old_m_dict, m_vals, ['name', 'sequence', 'active']):
                m_change_type = 'unchanged'
                m_msg = _("Menu in sync.")
            else:
                m_change_type = 'update' if self.on_conflict == 'overwrite' else 'exists'
                m_msg = _("Menu differs.")
        return {
            'object_type': 'menu',
            'change_type': m_change_type,
            'name': f"menu: {m_item['name']}",
            'target_ref': target_xml_id,
            'old_raw': m_old_raw,
            'new_raw': new_m_raw,
            'message': m_msg,
        }

    def _plan_window_action_and_menus(self, src_act, tname, ctx):
        changes = self._plan_one_window_action(src_act, tname, ctx)
        menus = ctx['source_rpc'].search_read(
            'ir.ui.menu', [('action', '=', 'ir.actions.act_window,%s' % src_act['id'])],
            ['name', 'parent_id', 'sequence', 'active', 'web_icon'],
        )
        for m_item in menus:
            changes.append(self._plan_one_menu_item(m_item, tname, ctx))
        return changes

    @staticmethod
    def _read_model_name(rpc, many2one_val):
        if not many2one_val:
            return False
        mid = many2one_val[0] if isinstance(many2one_val, (list, tuple)) else many2one_val
        rec = rpc.read('ir.model', [mid], ['model'])
        return rec[0]['model'] if rec else False

    def _plan_menus_for_model(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        target_mod = ctx.get('target_module') or 'meta_migrator'
        actions = ctx['source_rpc'].search_read(
            'ir.actions.act_window', [('res_model', '=', m)], [
                'id', 'name', 'res_model', 'view_mode', 'domain', 'context', 'limit', 'target', 'help',
            ],
        )
        if not actions:
            st, _tmid = self._target_model_state(ctx, tname)
            has_tgt_action = False
            if st == 'real':
                res = ctx['target_rpc'].search_read(
                    'ir.actions.act_window', [('res_model', '=', tname)], ['id'], limit=1,
                )
                has_tgt_action = bool(res)
            if not has_tgt_action:
                src_row = ctx['source_rpc'].search_read('ir.model', [('model', '=', m)], ['name'], limit=1)
                act_name = src_row[0]['name'] if src_row else tname
                target_xml_id = build_xml_id(target_mod, 'menu', act_name)
                new_m_dict = {
                    'name': act_name,
                    'sequence': 10,
                    'active': True,
                    'action': f"ir.actions.act_window for {tname}",
                }
                return [{
                    'object_type': 'menu',
                    'change_type': 'create',
                    'name': f"menu: {act_name}",
                    'target_ref': target_xml_id,
                    'old_raw': '',
                    'new_raw': dump_json(new_m_dict),
                    'message': _("Auto-generate menu and window action for %s") % tname,
                }]
            return [{
                'object_type': 'menu',
                'change_type': 'unchanged',
                'name': f"menus for {m}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("Window action / menu already exists on target for %s.") % tname,
            }]

        changes = []
        for src_act in actions:
            changes.extend(self._plan_window_action_and_menus(src_act, tname, ctx))
        return changes

    def _plan_access_right(self, step, ctx):
        if step.get('xml_id'):
            return self._plan_access_right_by_xml_id(step, ctx)
        return self._plan_access_rights_for_model(step, ctx)

    def _plan_access_right_by_xml_id(self, step, ctx):
        xml_id = step['xml_id']
        if '.' not in xml_id:
            return [{
                'object_type': 'access_right',
                'change_type': 'error',
                'name': f"access {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Invalid XML ID '%s'. Use module.name format.") % xml_id,
            }]
        module, name = xml_id.split('.', 1)
        src_data = ctx['source_rpc'].search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.model.access')],
            ['res_id', 'model'], limit=1,
        )
        if not src_data:
            return [{
                'object_type': 'access_right',
                'change_type': 'error',
                'name': f"access {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Access right with XML ID '%s' was not found on source.") % xml_id,
            }]

        acc_recs = ctx['source_rpc'].read(
            'ir.model.access', [src_data[0]['res_id']],
            ['name', 'model_id', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'],
        )
        if not acc_recs:
            return []
        acc = acc_recs[0]
        src_m = self._read_model_name(ctx['source_rpc'], acc.get('model_id')) or step.get('model_name') or ''
        tname = ctx['rename_map'].get(src_m, src_m)

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
            return [{
                'object_type': 'access_right',
                'change_type': 'exists',
                'name': f"access {acc['name']}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': new_raw,
                'message': _("Source group '%s' cannot be mapped on target link; skipped.") % group_ref,
            }]

        st, tmid = self._target_model_state(ctx, tname)
        tgt_data = ctx['target_rpc'].search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.model.access')],
            ['res_id'], limit=1,
        )
        existing = None
        if tgt_data:
            tgt_accs = ctx['target_rpc'].read(
                'ir.model.access', [tgt_data[0]['res_id']],
                ['name', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'],
            )
            if tgt_accs:
                existing = tgt_accs[0]
        if not existing and st == 'real':
            domain = [('model_id', '=', tmid), ('name', '=', acc['name'])]
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
                'name': f"access {acc['name']}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': new_raw,
                'message': _("Create access right %s (%s)") % (acc['name'], xml_id),
            }]

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
            'name': f"access {acc['name']}",
            'target_ref': xml_id,
            'old_raw': old_raw,
            'new_raw': new_raw,
            'message': msg,
        }]

    def _plan_access_rights_for_model(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        target_mod = ctx.get('target_module') or 'meta_migrator'

        access_records = ctx['source_rpc'].search_read(
            'ir.model.access', [('model_id.model', '=', m)], [
                'id', 'name', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'],
        )
        if not access_records:
            st, tmid = self._target_model_state(ctx, tname)
            has_tgt_access = False
            if st == 'real':
                res = ctx['target_rpc'].search_read(
                    'ir.model.access', [('model_id', '=', tmid)], ['id'], limit=1,
                )
                has_tgt_access = bool(res)
            if not has_tgt_access:
                clean_m = tname.replace('.', '_')
                target_xml_id = build_xml_id(target_mod, 'access_right', f"access_{clean_m}", model_name=tname)
                new_vals = {
                    'name': f"access_{clean_m}",
                    'model': tname,
                    'group': 'All',
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                }
                return [{
                    'object_type': 'access_right',
                    'change_type': 'create',
                    'name': f"access {clean_m}",
                    'target_ref': target_xml_id,
                    'old_raw': '',
                    'new_raw': dump_json(new_vals),
                    'message': _("Auto-generate default access right for %s") % tname,
                }]
            return [{
                'object_type': 'access_right',
                'change_type': 'unchanged',
                'name': f"access rights for {tname}",
                'target_ref': tname,
                'old_raw': '',
                'new_raw': '',
                'message': _("Access rights already exist on target for model %s.") % tname,
            }]

        changes = []
        for acc in access_records:
            src_data = ctx['source_rpc'].search_read(
                'ir.model.data',
                [('model', '=', 'ir.model.access'), ('res_id', '=', acc['id'])],
                ['module', 'name'], limit=1,
            )
            src_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}" if (src_data and src_data[0].get('module') and src_data[0].get('name')) else False
            target_xml_id = src_xml_id or build_xml_id(target_mod, 'access_right', acc['name'], model_name=tname)
            target_ref = target_xml_id

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
                    'target_ref': target_ref,
                    'old_raw': '',
                    'new_raw': new_raw,
                    'message': _("Source group '%s' cannot be mapped on target link; skipped.") % group_ref,
                })
                continue

            st, tmid = self._target_model_state(ctx, tname)
            existing = None
            if '.' in target_xml_id:
                tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
                tgt_data = ctx['target_rpc'].search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.model.access')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    tgt_accs = ctx['target_rpc'].read(
                        'ir.model.access', [tgt_data[0]['res_id']],
                        ['name', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'],
                    )
                    if tgt_accs:
                        existing = tgt_accs[0]
            if not existing and st == 'real':
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
                    'target_ref': target_ref,
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
                    'target_ref': target_ref,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'message': msg,
                })

        return changes

    def _plan_record_rule(self, step, ctx):
        if step.get('xml_id'):
            return self._plan_record_rule_by_xml_id(step, ctx)
        return self._plan_record_rules_for_model(step, ctx)

    def _plan_record_rule_by_xml_id(self, step, ctx):
        xml_id = step['xml_id']
        if '.' not in xml_id:
            return [{
                'object_type': 'record_rule',
                'change_type': 'error',
                'name': f"rule {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Invalid XML ID '%s'. Use module.name format.") % xml_id,
            }]
        module, name = xml_id.split('.', 1)
        src_data = ctx['source_rpc'].search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.rule')],
            ['res_id', 'model'], limit=1,
        )
        if not src_data:
            return [{
                'object_type': 'record_rule',
                'change_type': 'error',
                'name': f"rule {xml_id}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': '',
                'message': _("Record rule with XML ID '%s' was not found on source.") % xml_id,
            }]

        rules = ctx['source_rpc'].read(
            'ir.rule', [src_data[0]['res_id']],
            ['name', 'model_id', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'],
        )
        if not rules:
            return []
        r = rules[0]
        src_m = self._read_model_name(ctx['source_rpc'], r.get('model_id')) or step.get('model_name') or ''
        tname = ctx['rename_map'].get(src_m, src_m)

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
        tgt_data = ctx['target_rpc'].search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.rule')],
            ['res_id'], limit=1,
        )
        existing = None
        if tgt_data:
            tgt_rules = ctx['target_rpc'].read(
                'ir.rule', [tgt_data[0]['res_id']],
                ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'],
            )
            if tgt_rules:
                existing = tgt_rules[0]
        if not existing and st == 'real':
            res = ctx['target_rpc'].search_read(
                'ir.rule', [('model_id', '=', tmid), ('name', '=', r['name'])],
                ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'], limit=1,
            )
            if res:
                existing = res[0]

        if not existing:
            return [{
                'object_type': 'record_rule',
                'change_type': 'create',
                'name': f"rule {r['name']}",
                'target_ref': xml_id,
                'old_raw': '',
                'new_raw': new_raw,
                'message': _("Create record rule %s (%s)") % (r['name'], xml_id),
            }]

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
            'name': f"rule {r['name']}",
            'target_ref': xml_id,
            'old_raw': old_raw,
            'new_raw': new_raw,
            'message': msg,
        }]

    def _plan_record_rules_for_model(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        target_mod = ctx.get('target_module') or 'meta_migrator'

        rules = ctx['source_rpc'].search_read(
            'ir.rule', [('model_id.model', '=', m)], [
                'id', 'name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active',
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
            src_data = ctx['source_rpc'].search_read(
                'ir.model.data',
                [('model', '=', 'ir.rule'), ('res_id', '=', r['id'])],
                ['module', 'name'], limit=1,
            )
            src_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}" if (src_data and src_data[0].get('module') and src_data[0].get('name')) else False
            target_xml_id = src_xml_id or build_xml_id(target_mod, 'record_rule', r['name'], model_name=tname)
            target_ref = target_xml_id

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
            if '.' in target_xml_id:
                tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
                tgt_data = ctx['target_rpc'].search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.rule')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    tgt_rules = ctx['target_rpc'].read(
                        'ir.rule', [tgt_data[0]['res_id']],
                        ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'],
                    )
                    if tgt_rules:
                        existing = tgt_rules[0]
            if not existing and st == 'real':
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
                    'target_ref': target_ref,
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
                    'target_ref': target_ref,
                    'old_raw': old_raw,
                    'new_raw': new_raw,
                    'message': msg,
                })

        return changes
