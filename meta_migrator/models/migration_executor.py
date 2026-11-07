import logging
from odoo import api, models, _
from odoo.exceptions import UserError

from .rpc_helper import OdooRPCError
from .diff_utils import build_xml_id, replace_action_references_in_arch, sync_action_id_in_target_views
from . import view_merge

_logger = logging.getLogger(__name__)

FIELD_CORE_KEYS = [
    'name', 'field_description', 'ttype', 'required', 'readonly',
    'store', 'index', 'copied', 'help', 'relation', 'relation_field',
    'on_delete', 'domain', 'selection', 'translate',
]
FIELD_LOGIC_KEYS = ['compute', 'depends', 'related']
ALL_FIELD_KEYS = FIELD_CORE_KEYS + FIELD_LOGIC_KEYS


class MetaMigrationExecutor(models.AbstractModel):
    _name = 'meta.migration.executor'
    _description = 'Migration Push Logic & Application Mixin'

    def _record_item_and_commit(self, ctx, object_type, model_name, name, xml_id, res_id=False, state='applied', message=False):
        job = (ctx and ctx.get('job')) or (hasattr(self, 'job_id') and self.job_id)
        if job and xml_id:
            job.record_migrated_item(
                object_type=object_type,
                model_name=model_name,
                name=name,
                xml_id=xml_id,
                res_id=res_id,
                state=state,
                message=message,
            )
        if hasattr(self, '_safe_commit'):
            self._safe_commit()

    @staticmethod
    def _build_field_vals(fvals, rename_map):
        vals = {k: fvals[k] for k in FIELD_CORE_KEYS if fvals.get(k) not in (False, None, '')}
        vals['store'] = fvals.get('store', True)
        if fvals.get('ttype') in ('many2one', 'one2many', 'many2many') and vals.get('relation'):
            vals['relation'] = rename_map.get(vals['relation'], vals['relation'])
        return vals

    @staticmethod
    def _build_view_vals(view, target_model_name, vtype):
        return {
            'name': view['name'],
            'model': target_model_name,
            'type': vtype,
            'arch': view['arch'],
            'priority': view.get('priority', 16),
        }

    @staticmethod
    def _build_server_action_vals(action, target_model_id, binding_model_id):
        vals = {
            'name': action['name'],
            'state': action.get('state') or 'code',
            'code': action.get('code'),
        }
        if target_model_id:
            vals['model_id'] = target_model_id
        if binding_model_id:
            vals['binding_model_id'] = binding_model_id
            vals['binding_type'] = action.get('binding_type') or 'action'
        return vals

    def _load_model_map(self, cache):
        key = ('rename_map', self.source_connection_id.id, self.target_connection_id.id)
        if key not in cache:
            mappings = self.env['meta.migration.model.map'].search_read([
                ('source_connection_id', '=', self.source_connection_id.id),
                ('target_connection_id', '=', self.target_connection_id.id),
            ], ['source_model', 'target_model'])
            cache[key] = {
                item['source_model']: item['target_model']
                for item in mappings
            }
        return cache[key]

    def _get_target_model_id_strict(self, target_rpc, model_name, rename_map, cache):
        target_model_name = rename_map.get(model_name, model_name)
        key = ('strict_model', target_model_name)
        if key not in cache:
            existing = target_rpc.search_read(
                'ir.model', [('model', '=', target_model_name)], ['id'], limit=1,
            )
            if not existing:
                raise UserError(
                    _("Model '%s' does not exist on the target system. "
                      "Run a 'create model' step first.") % target_model_name
                )
            cache[key] = existing[0]['id']
        return cache[key]

    def _ensure_target_model(self, target_rpc, model_info, target_model_name, cache, ctx=None):
        key = ('model', target_model_name)
        if key in cache:
            return cache[key]

        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        target_xml_id = build_xml_id(target_mod, 'model', target_model_name)

        existing = target_rpc.search_read('ir.model', [('model', '=', target_model_name)], ['id'])
        if existing:
            target_id = existing[0]['id']
        elif model_info.get('state') == 'manual':
            target_id = target_rpc.create('ir.model', {
                'name': model_info['name'],
                'model': target_model_name,
                'state': 'manual',
                'transient': model_info.get('transient', False),
            })
        else:
            raise UserError(
                _("Standard model '%s' does not exist on the target system (target name: '%s'). "
                  "This model is code-defined (state != manual), so install the corresponding "
                  "module on the target before migrating fields.")
                % (model_info['model'], target_model_name)
            )
        self._create_xml_id(target_rpc, target_xml_id, 'ir.model', target_id)
        self._record_item_and_commit(ctx, 'model', target_model_name, target_model_name, target_xml_id, res_id=target_id)
        cache[key] = target_id
        return target_id

    @staticmethod
    def _sort_fields_pass1(field_vals):
        non_o2m = [f for f in field_vals if f.get('ttype') != 'one2many']
        o2m = [f for f in field_vals if f.get('ttype') == 'one2many']
        return non_o2m + o2m

    def _write_field_pass1(self, target_rpc, target_model_id, target_model_name, fvals, rename_map, ctx=None):
        vals = self._build_field_vals(fvals, rename_map)
        vals.update({
            'model_id': target_model_id,
            'model': target_model_name,
            'state': 'manual',
        })
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        target_xml_id = fvals.get('xml_id') or build_xml_id(target_mod, 'field', fvals['name'], model_name=target_model_name)

        if fvals.get('ttype') == 'one2many':
            rel_model = rename_map.get(fvals.get('relation', ''), fvals.get('relation', ''))
            rel_field = fvals.get('relation_field', '')
            if rel_model and rel_field:
                rel_model_rows = target_rpc.search_read(
                    'ir.model', [('model', '=', rel_model)], ['id'], limit=1,
                )
                if not rel_model_rows:
                    raise UserError(_(
                        "Cannot create one2many field '%s.%s': target relational model '%s' does not exist on target. "
                        "Ensure the model is created first."
                    ) % (target_model_name, fvals['name'], rel_model))
                rel_field_rows = target_rpc.search_read(
                    'ir.model.fields',
                    [('model_id', '=', rel_model_rows[0]['id']), ('name', '=', rel_field)],
                    ['id'], limit=1,
                )
                if not rel_field_rows:
                    raise UserError(_(
                        "Cannot create one2many field '%s.%s': "
                        "relation_field '%s' does not exist on model '%s' on target. "
                        "Ensure the many2one field step runs before this step."
                    ) % (target_model_name, fvals['name'], rel_field, rel_model))

        if fvals.get('ttype') in ('many2one', 'many2many'):
            rel_model = rename_map.get(fvals.get('relation', ''), fvals.get('relation', ''))
            if rel_model:
                rel_model_rows = target_rpc.search_read(
                    'ir.model', [('model', '=', rel_model)], ['id'], limit=1,
                )
                if not rel_model_rows:
                    raise UserError(_(
                        "Cannot create %s field '%s.%s': target relational model '%s' does not exist on target. "
                        "Ensure the model is created first."
                    ) % (fvals.get('ttype'), target_model_name, fvals['name'], rel_model))

        existing = target_rpc.search_read(
            'ir.model.fields',
            [('model_id', '=', target_model_id), ('name', '=', fvals['name'])],
            ['id'],
        )
        if existing:
            target_id = existing[0]['id']
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.model.fields', [target_id], vals)
        else:
            target_id = target_rpc.create('ir.model.fields', vals)

        self._create_xml_id(target_rpc, target_xml_id, 'ir.model.fields', target_id)
        self._record_item_and_commit(ctx, 'field', target_model_name, fvals['name'], target_xml_id, res_id=target_id)
        return target_id

    def _write_field_pass2(self, target_rpc, target_model_id, field_name, logic_vals):
        existing = target_rpc.search_read(
            'ir.model.fields',
            [('model_id', '=', target_model_id), ('name', '=', field_name)],
            ['id'],
        )
        if not existing:
            raise OdooRPCError(
                _("Field '%s' does not exist on the target (pass 1 may have failed).") % field_name
            )
        target_rpc.write('ir.model.fields', [existing[0]['id']], logic_vals)

    def _find_or_create_window_action(self, source_rpc, target_rpc, source_action, target_model_name, cache, ctx=None):
        source_xml_id = self._get_xml_id(
            source_rpc, 'ir.actions.act_window', source_action['id'], cache,
        )
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        target_xml_id = source_xml_id or build_xml_id(target_mod, 'action', source_action['name'], model_name=target_model_name)
        vals = {
            'name': source_action['name'],
            'res_model': target_model_name,
            'view_mode': source_action.get('view_mode') or 'list,form',
            'domain': source_action.get('domain') or '[]',
            'context': source_action.get('context') or '{}',
            'limit': source_action.get('limit', 80),
            'target': source_action.get('target') or 'current',
            'help': source_action.get('help') or False,
        }
        target_id = False
        if target_xml_id:
            target_id = self._find_target_by_xml_id(
                target_rpc, target_xml_id, 'ir.actions.act_window',
            )
        if not target_id:
            existing = target_rpc.search_read(
                'ir.actions.act_window', [
                    ('name', '=', source_action['name']),
                    ('res_model', '=', target_model_name),
                ], ['id'], limit=1,
            )
            target_id = existing[0]['id'] if existing else False

        if target_id:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.actions.act_window', [target_id], vals)
        else:
            target_id = target_rpc.create('ir.actions.act_window', vals)

        self._create_xml_id(
            target_rpc, target_xml_id, 'ir.actions.act_window', target_id,
        )
        self._record_item_and_commit(ctx, 'menu', target_model_name, source_action['name'], target_xml_id, res_id=target_id)
        return target_id

    def _find_or_create_menu(self, source_rpc, target_rpc, source_menu, action_id, cache, ctx=None):
        source_xml_id = self._get_xml_id(
            source_rpc, 'ir.ui.menu', source_menu['id'], cache,
        )
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        target_xml_id = source_xml_id or build_xml_id(target_mod, 'menu', source_menu['name'])
        parent_id = self._find_target_menu_parent(
            source_rpc, target_rpc, source_menu, cache,
        )
        vals = {
            'name': source_menu['name'],
            'parent_id': parent_id or False,
            'sequence': source_menu.get('sequence', 10),
            'active': source_menu.get('active', True),
            'action': ('ir.actions.act_window,%s' % action_id) if action_id else False,
        }
        if source_menu.get('web_icon'):
            vals['web_icon'] = source_menu['web_icon']

        target_id = False
        if target_xml_id:
            target_id = self._find_target_by_xml_id(
                target_rpc, target_xml_id, 'ir.ui.menu',
            )
        if not target_id:
            domain = [('name', '=', source_menu['name'])]
            if vals['action']:
                domain.append(('action', '=', vals['action']))
            domain.append(('parent_id', '=', parent_id or False))
            existing = target_rpc.search_read('ir.ui.menu', domain, ['id'], limit=1)
            target_id = existing[0]['id'] if existing else False

        if target_id:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.ui.menu', [target_id], vals)
        else:
            target_id = target_rpc.create('ir.ui.menu', vals)

        self._create_xml_id(target_rpc, target_xml_id, 'ir.ui.menu', target_id)
        self._record_item_and_commit(ctx, 'menu', False, source_menu['name'], target_xml_id, res_id=target_id)
        return target_id

    def _find_target_menu_parent(self, source_rpc, target_rpc, source_menu, cache):
        parent = source_menu.get('parent_id')
        if not parent:
            return False
        source_parent_id = parent[0]
        key = ('menu_parent', source_parent_id)
        if key in cache:
            return cache[key]

        source_parent = source_rpc.search_read(
            'ir.ui.menu', [('id', '=', source_parent_id)],
            ['name', 'parent_id', 'sequence', 'active', 'web_icon'], limit=1,
        )
        if not source_parent:
            cache[key] = False
            return False
        source_parent = source_parent[0]
        source_xml_id = self._get_xml_id(
            source_rpc, 'ir.ui.menu', source_parent_id, cache,
        )
        target_id = self._find_target_by_xml_id(
            target_rpc, source_xml_id, 'ir.ui.menu',
        ) if source_xml_id else False
        if not target_id:
            target_parent_id = self._find_target_menu_parent(
                source_rpc, target_rpc, source_parent, cache,
            )
            existing = target_rpc.search_read(
                'ir.ui.menu', [
                    ('name', '=', source_parent['name']),
                    ('parent_id', '=', target_parent_id or False),
                ], ['id'], limit=1,
            )
            target_id = existing[0]['id'] if existing else False
            if not target_id:
                target_id = target_rpc.create('ir.ui.menu', {
                    'name': source_parent['name'],
                    'parent_id': target_parent_id or False,
                    'sequence': source_parent.get('sequence', 10),
                    'active': source_parent.get('active', True),
                })
                if source_xml_id:
                    self._create_xml_id(
                        target_rpc, source_xml_id, 'ir.ui.menu', target_id,
                    )
        cache[key] = target_id
        return target_id

    @staticmethod
    def _get_xml_id(rpc, model_name, record_id, cache):
        key = ('xml_id', model_name, record_id)
        if key not in cache:
            data = rpc.search_read(
                'ir.model.data', [
                    ('model', '=', model_name), ('res_id', '=', record_id),
                ], ['module', 'name'], limit=1,
            )
            cache[key] = (
                '%s.%s' % (data[0]['module'], data[0]['name'])
                if data else False
            )
        return cache[key]

    @staticmethod
    def _find_target_by_xml_id(rpc, xml_id, model_name):
        if not xml_id or '.' not in xml_id:
            return False
        module, name = xml_id.split('.', 1)
        data = rpc.search_read(
            'ir.model.data', [
                ('module', '=', module), ('name', '=', name),
                ('model', '=', model_name),
            ], ['res_id'], limit=1,
        )
        return data[0]['res_id'] if data else False

    @staticmethod
    def _create_xml_id(rpc, xml_id, model_name, record_id):
        module, name = xml_id.split('.', 1)
        existing = rpc.search_read(
            'ir.model.data', [
                ('module', '=', module), ('name', '=', name),
            ], ['id'], limit=1,
        )
        if not existing:
            rpc.create('ir.model.data', {
                'module': module,
                'name': name,
                'model': model_name,
                'res_id': record_id,
                'noupdate': True,
            })

    def _map_group_id(self, source_rpc, target_rpc, source_group_id, cache):
        if not source_group_id:
            return False
        key = ('group', source_group_id)
        if key in cache:
            return cache[key]

        source_data = source_rpc.search_read(
            'ir.model.data', [
                ('model', '=', 'res.groups'),
                ('res_id', '=', source_group_id),
            ], ['module', 'name'], limit=1,
        )
        if not source_data:
            cache[key] = False
            return False
        data = source_data[0]
        target_data = target_rpc.search_read(
            'ir.model.data', [
                ('model', '=', 'res.groups'),
                ('module', '=', data['module']),
                ('name', '=', data['name']),
            ], ['res_id'], limit=1,
        )
        cache[key] = target_data[0]['res_id'] if target_data else False
        return cache[key]

    def _migrate_access_rights(self, source_rpc, target_rpc, model_name, target_model_id, cache, ctx=None):
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        messages = []
        access_records = source_rpc.search_read(
            'ir.model.access', [('model_id.model', '=', model_name)], [
                'id', 'name', 'group_id', 'perm_read', 'perm_write',
                'perm_create', 'perm_unlink',
            ],
        )
        if not access_records:
            clean_m = model_name.replace('.', '_')
            target_xml_id = build_xml_id(target_mod, 'access_right', f"access_{clean_m}", model_name=model_name)
            existing = None
            if '.' in target_xml_id:
                tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
                tgt_data = target_rpc.search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.model.access')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    existing = tgt_data[0]['res_id']
            if not existing:
                res = target_rpc.search_read(
                    'ir.model.access', [('model_id', '=', target_model_id)], ['id'], limit=1,
                )
                if res:
                    existing = res[0]['id']
            if not existing:
                vals = {
                    'name': f"access_{clean_m}",
                    'model_id': target_model_id,
                    'group_id': False,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                }
                new_id = target_rpc.create('ir.model.access', vals)
                self._create_xml_id(target_rpc, target_xml_id, 'ir.model.access', new_id)
                self._record_item_and_commit(ctx, 'access_right', model_name, f"access_{clean_m}", target_xml_id, res_id=new_id)
                messages.append(_(" - Default access right 'access_%s': created automatically.") % clean_m)
            return messages

        for access in access_records:
            source_group = access.get('group_id')
            source_group_id = source_group[0] if source_group else False
            target_group_id = self._map_group_id(
                source_rpc, target_rpc, source_group_id, cache,
            )
            if source_group_id and not target_group_id:
                messages.append(_(" - Access '%s': source group could not be mapped; skipped.") % access['name'])
                continue

            src_data = source_rpc.search_read(
                'ir.model.data',
                [('model', '=', 'ir.model.access'), ('res_id', '=', access['id'])],
                ['module', 'name'], limit=1,
            )
            src_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}" if (src_data and src_data[0].get('module') and src_data[0].get('name')) else False
            target_xml_id = src_xml_id or build_xml_id(target_mod, 'access_right', access['name'], model_name=model_name)

            vals = {
                'name': access['name'],
                'model_id': target_model_id,
                'group_id': target_group_id or False,
                'perm_read': access.get('perm_read', False),
                'perm_write': access.get('perm_write', False),
                'perm_create': access.get('perm_create', False),
                'perm_unlink': access.get('perm_unlink', False),
            }
            existing = None
            if '.' in target_xml_id:
                tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
                tgt_data = target_rpc.search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.model.access')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    existing = tgt_data[0]['res_id']
            if not existing:
                res = target_rpc.search_read(
                    'ir.model.access', [
                        ('model_id', '=', target_model_id),
                        ('name', '=', access['name']),
                    ], ['id'], limit=1,
                )
                if res:
                    existing = res[0]['id']

            if existing and self.on_conflict == 'overwrite':
                target_rpc.write('ir.model.access', [existing], vals)
                self._create_xml_id(target_rpc, target_xml_id, 'ir.model.access', existing)
                self._record_item_and_commit(ctx, 'access_right', model_name, access['name'], target_xml_id, res_id=existing)
                messages.append(_(" - Access '%s': overwritten.") % access['name'])
            elif existing:
                messages.append(_(" - Access '%s': already exists, skipped.") % access['name'])
            else:
                target_id = target_rpc.create('ir.model.access', vals)
                self._create_xml_id(target_rpc, target_xml_id, 'ir.model.access', target_id)
                self._record_item_and_commit(ctx, 'access_right', model_name, access['name'], target_xml_id, res_id=target_id)
                messages.append(_(" - Access '%s': migrated successfully.") % access['name'])
        return messages

    def _migrate_record_rules(self, source_rpc, target_rpc, model_name, target_model_id, cache, ctx=None):
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        messages = []
        rules = source_rpc.search_read(
            'ir.rule', [('model_id.model', '=', model_name)], [
                'id', 'name', 'domain_force', 'groups', 'perm_read', 'perm_write',
                'perm_create', 'perm_unlink', 'active',
            ],
        )
        for rule in rules:
            source_group_ids = rule.get('groups') or []
            target_group_ids = []
            for source_group_id in source_group_ids:
                target_group_id = self._map_group_id(
                    source_rpc, target_rpc, source_group_id, cache,
                )
                if target_group_id:
                    target_group_ids.append(target_group_id)
                else:
                    messages.append(_(" - Rule '%s': a group could not be mapped; continuing without it.") % rule['name'])

            src_data = source_rpc.search_read(
                'ir.model.data',
                [('model', '=', 'ir.rule'), ('res_id', '=', rule['id'])],
                ['module', 'name'], limit=1,
            )
            src_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}" if (src_data and src_data[0].get('module') and src_data[0].get('name')) else False
            target_xml_id = src_xml_id or build_xml_id(target_mod, 'record_rule', rule['name'], model_name=model_name)

            vals = {
                'name': rule['name'],
                'model_id': target_model_id,
                'domain_force': rule.get('domain_force') or '',
                'groups': [(6, 0, target_group_ids)],
                'perm_read': rule.get('perm_read', False),
                'perm_write': rule.get('perm_write', False),
                'perm_create': rule.get('perm_create', False),
                'perm_unlink': rule.get('perm_unlink', False),
                'active': rule.get('active', True),
            }
            existing = None
            if '.' in target_xml_id:
                tgt_m_mod, tgt_m_name = target_xml_id.split('.', 1)
                tgt_data = target_rpc.search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.rule')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    existing = tgt_data[0]['res_id']
            if not existing:
                res = target_rpc.search_read(
                    'ir.rule', [
                        ('model_id', '=', target_model_id),
                        ('name', '=', rule['name']),
                    ], ['id'], limit=1,
                )
                if res:
                    existing = res[0]['id']

            if existing and self.on_conflict == 'overwrite':
                target_rpc.write('ir.rule', [existing], vals)
                self._create_xml_id(target_rpc, target_xml_id, 'ir.rule', existing)
                self._record_item_and_commit(ctx, 'record_rule', model_name, rule['name'], target_xml_id, res_id=existing)
                messages.append(_(" - Rule '%s': overwritten.") % rule['name'])
            elif existing:
                messages.append(_(" - Rule '%s': already exists, skipped.") % rule['name'])
            else:
                target_id = target_rpc.create('ir.rule', vals)
                self._create_xml_id(target_rpc, target_xml_id, 'ir.rule', target_id)
                self._record_item_and_commit(ctx, 'record_rule', model_name, rule['name'], target_xml_id, res_id=target_id)
                messages.append(_(" - Rule '%s': migrated successfully.") % rule['name'])
        return messages

    def _migrate_access_right_by_xml_id(self, source_rpc, target_rpc, xml_id, rename_map, cache, ctx=None):
        if '.' not in xml_id:
            raise UserError(_("Invalid XML ID '%s'.") % xml_id)
        module, name = xml_id.split('.', 1)
        src_data = source_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.model.access')],
            ['res_id', 'model'], limit=1,
        )
        if not src_data:
            raise UserError(_("Access right with XML ID '%s' not found on source.") % xml_id)

        acc_recs = source_rpc.read(
            'ir.model.access', [src_data[0]['res_id']],
            ['name', 'model_id', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'],
        )
        if not acc_recs:
            return []
        acc = acc_recs[0]
        src_m = self._read_model_name(source_rpc, acc.get('model_id'))
        if not src_m:
            raise UserError(_("Could not resolve model for access right '%s'.") % xml_id)
        tmid = self._get_target_model_id_strict(target_rpc, src_m, rename_map, cache)

        source_group = acc.get('group_id')
        source_group_id = source_group[0] if source_group else False
        target_group_id = self._map_group_id(source_rpc, target_rpc, source_group_id, cache)

        vals = {
            'name': acc['name'],
            'model_id': tmid,
            'group_id': target_group_id or False,
            'perm_read': acc.get('perm_read', False),
            'perm_write': acc.get('perm_write', False),
            'perm_create': acc.get('perm_create', False),
            'perm_unlink': acc.get('perm_unlink', False),
        }

        tgt_data = target_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.model.access')],
            ['res_id'], limit=1,
        )
        existing = None
        if tgt_data:
            existing = tgt_data[0]['res_id']
        else:
            acc_tgt = target_rpc.search_read(
                'ir.model.access',
                [('model_id', '=', tmid), ('name', '=', acc['name'])],
                ['id'], limit=1,
            )
            if acc_tgt:
                existing = acc_tgt[0]['id']

        if existing:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.model.access', [existing], vals)
                self._create_xml_id(target_rpc, xml_id, 'ir.model.access', existing)
                self._record_item_and_commit(ctx, 'access_right', src_m, acc['name'], xml_id, res_id=existing)
                return [_("Access right '%s': overwritten.") % acc['name']]
            return [_("Access right '%s': already exists, skipped.") % acc['name']]

        new_id = target_rpc.create('ir.model.access', vals)
        self._create_xml_id(target_rpc, xml_id, 'ir.model.access', new_id)
        self._record_item_and_commit(ctx, 'access_right', src_m, acc['name'], xml_id, res_id=new_id)
        return [_("Access right '%s': created successfully.") % acc['name']]

    def _migrate_record_rule_by_xml_id(self, source_rpc, target_rpc, xml_id, rename_map, cache, ctx=None):
        if '.' not in xml_id:
            raise UserError(_("Invalid XML ID '%s'.") % xml_id)
        module, name = xml_id.split('.', 1)
        src_data = source_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.rule')],
            ['res_id', 'model'], limit=1,
        )
        if not src_data:
            raise UserError(_("Record rule with XML ID '%s' not found on source.") % xml_id)

        rules = source_rpc.read(
            'ir.rule', [src_data[0]['res_id']],
            ['name', 'model_id', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'],
        )
        if not rules:
            return []
        rule = rules[0]
        src_m = self._read_model_name(source_rpc, rule.get('model_id'))
        if not src_m:
            raise UserError(_("Could not resolve model for record rule '%s'.") % xml_id)
        tmid = self._get_target_model_id_strict(target_rpc, src_m, rename_map, cache)

        source_group_ids = rule.get('groups') or []
        target_group_ids = []
        for source_group_id in source_group_ids:
            tgt_gid = self._map_group_id(source_rpc, target_rpc, source_group_id, cache)
            if tgt_gid:
                target_group_ids.append(tgt_gid)

        vals = {
            'name': rule['name'],
            'model_id': tmid,
            'domain_force': rule.get('domain_force') or '',
            'groups': [(6, 0, target_group_ids)],
            'perm_read': rule.get('perm_read', False),
            'perm_write': rule.get('perm_write', False),
            'perm_create': rule.get('perm_create', False),
            'perm_unlink': rule.get('perm_unlink', False),
            'active': rule.get('active', True),
        }

        tgt_data = target_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.rule')],
            ['res_id'], limit=1,
        )
        existing = None
        if tgt_data:
            existing = tgt_data[0]['res_id']
        else:
            rule_tgt = target_rpc.search_read(
                'ir.rule',
                [('model_id', '=', tmid), ('name', '=', rule['name'])],
                ['id'], limit=1,
            )
            if rule_tgt:
                existing = rule_tgt[0]['id']

        if existing:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.rule', [existing], vals)
                self._create_xml_id(target_rpc, xml_id, 'ir.rule', existing)
                self._record_item_and_commit(ctx, 'record_rule', src_m, rule['name'], xml_id, res_id=existing)
                return [_("Record rule '%s': overwritten.") % rule['name']]
            return [_("Record rule '%s': already exists, skipped.") % rule['name']]

        new_id = target_rpc.create('ir.rule', vals)
        self._create_xml_id(target_rpc, xml_id, 'ir.rule', new_id)
        self._record_item_and_commit(ctx, 'record_rule', src_m, rule['name'], xml_id, res_id=new_id)
        return [_("Record rule '%s': created successfully.") % rule['name']]

    def _migrate_view(self, source_rpc, target_rpc, model_name, target_model_name, vtype, ctx=None):
        search_types = [vtype] if vtype != 'list' else ['list', 'tree']
        views = source_rpc.search_read(
            'ir.ui.view',
            [('model', '=', model_name), ('type', 'in', search_types), ('active', '=', True)],
            ['id', 'name', 'type', 'arch', 'priority', 'inherit_id', 'mode'],
        )
        if not views:
            return _(" - View '%s' for model '%s': not found on source, skipped.") % (vtype, model_name)

        views.sort(key=lambda v: v.get('priority', 16))
        view = views[0]
        return self._migrate_one_view(source_rpc, target_rpc, view, target_model_name, {}, ctx=ctx)

    def _migrate_views_for_model(self, source_rpc, target_rpc, model_name, target_model_name, cache, vtype=None, ctx=None):
        domain = [('model', '=', model_name), ('active', '=', True)]
        if vtype:
            search_types = [vtype] if vtype != 'list' else ['list', 'tree']
            domain.append(('type', 'in', search_types))
        views = source_rpc.search_read(
            'ir.ui.view',
            domain,
            ['id', 'name', 'type', 'arch', 'priority', 'inherit_id', 'mode'],
        )
        if not views:
            return [_("Views for model '%s': not found on source, skipped.") % model_name]

        views.sort(key=lambda v: v.get('priority', 16))
        messages = []
        for view in views:
            msg = self._migrate_one_view(source_rpc, target_rpc, view, target_model_name, cache, ctx=ctx)
            messages.append(msg)
        return messages

    def _migrate_one_view(self, source_rpc, target_rpc, view, target_model_name, cache, ctx=None):
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        src_data = source_rpc.search_read(
            'ir.model.data',
            [('model', '=', 'ir.ui.view'), ('res_id', '=', view['id'])],
            ['module', 'name'], limit=1,
        )
        src_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}" if src_data else False
        vtype = view.get('type') or 'form'
        vals = self._build_view_vals(view, target_model_name, vtype)
        if view.get('mode'):
            vals['mode'] = view['mode']

        if vals.get('arch'):
            vals['arch'] = replace_action_references_in_arch(vals['arch'], source_rpc, target_rpc, target_mod, cache)

        if view.get('inherit_id'):
            src_inherit_id = view['inherit_id'][0]
            parent_xml_id = self._get_xml_id(source_rpc, 'ir.ui.view', src_inherit_id, cache)
            if parent_xml_id:
                tgt_parent_id = self._find_target_by_xml_id(target_rpc, parent_xml_id, 'ir.ui.view')
                if tgt_parent_id:
                    vals['inherit_id'] = tgt_parent_id

        target_xml_id = src_xml_id or build_xml_id(target_mod, 'view', view['name'], model_name=target_model_name)
        target_id = False
        if target_xml_id:
            target_id = self._find_target_by_xml_id(target_rpc, target_xml_id, 'ir.ui.view')
        if not target_id:
            existing = target_rpc.search_read(
                'ir.ui.view',
                [('model', '=', target_model_name), ('type', '=', vtype), ('name', '=', view['name'])],
                ['id'], limit=1,
            )
            target_id = existing[0]['id'] if existing else False

        if target_id:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.ui.view', [target_id], vals)
                self._create_xml_id(target_rpc, target_xml_id, 'ir.ui.view', target_id)
                self._record_item_and_commit(ctx, 'view', target_model_name, view['name'], target_xml_id, res_id=target_id)
                return _(" - View '%s' (%s) for model '%s': overwritten.") % (view['name'], vtype, target_model_name)
            return _(" - View '%s' (%s) for model '%s': already exists, skipped.") % (view['name'], vtype, target_model_name)

        target_id = target_rpc.create('ir.ui.view', vals)
        self._create_xml_id(target_rpc, target_xml_id, 'ir.ui.view', target_id)
        self._record_item_and_commit(ctx, 'view', target_model_name, view['name'], target_xml_id, res_id=target_id)
        return _(" - View '%s' (%s) for model '%s': migrated successfully.") % (view['name'], vtype, target_model_name)

    def _migrate_view_by_xml_id(self, source_rpc, target_rpc, xml_id, rename_map, cache, ctx=None):
        if '.' not in xml_id:
            raise UserError(_("XML ID '%s' is invalid; use the module.name format.") % xml_id)
        module, name = xml_id.split('.', 1)
        data = source_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name)],
            ['res_id', 'model'], limit=1,
        )
        if not data or data[0]['model'] != 'ir.ui.view':
            raise UserError(_("View with XML ID '%s' was not found on the source system.") % xml_id)
        src_view = source_rpc.read(
            'ir.ui.view', [data[0]['res_id']],
            ['id', 'name', 'type', 'arch', 'priority', 'inherit_id', 'mode', 'model'],
        )[0]
        tgt_m = rename_map.get(src_view['model'], src_view['model'])
        return self._migrate_one_view(source_rpc, target_rpc, src_view, tgt_m, cache, ctx=ctx)

    def _migrate_server_action(self, source_rpc, target_rpc, xml_id, rename_map, cache, overwrite=None, ctx=None):
        if '.' not in xml_id:
            raise UserError(_("XML ID '%s' is invalid; use the module.name format.") % xml_id)
        module, name = xml_id.split('.', 1)

        data = source_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name)],
            ['res_id', 'model'],
        )
        if not data or data[0]['model'] != 'ir.actions.server':
            raise UserError(_("Server Action with XML ID '%s' was not found on the source system.") % xml_id)
        res_id = data[0]['res_id']

        action = source_rpc.read(
            'ir.actions.server', [res_id],
            ['name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'],
        )[0]

        src_model_name = self._read_model_name(source_rpc, action.get('model_id'))
        src_binding_model_name = self._read_model_name(source_rpc, action.get('binding_model_id'))

        target_model_id = False
        if src_model_name:
            target_model_id = self._get_target_model_id_strict(
                target_rpc, src_model_name, rename_map, cache,
            )
        binding_model_id = False
        if src_binding_model_name:
            binding_model_id = self._get_target_model_id_strict(
                target_rpc, src_binding_model_name, rename_map, cache,
            )

        vals = self._build_server_action_vals(action, target_model_id, binding_model_id)

        existing_data = target_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name)],
            ['res_id'],
        )
        should_overwrite = self.on_conflict == 'overwrite' if overwrite is None else overwrite
        if existing_data:
            target_id = existing_data[0]['res_id']
            if should_overwrite:
                target_rpc.write('ir.actions.server', [target_id], vals)
                self._record_item_and_commit(ctx, 'server_action', src_model_name, action['name'], xml_id, res_id=target_id)
                sync_action_id_in_target_views(target_rpc, res_id, xml_id)
                return _("Server Action '%s': overwritten.") % xml_id
            return _("Server Action '%s': already exists, skipped.") % xml_id

        target_id = target_rpc.create('ir.actions.server', vals)
        self._create_xml_id(target_rpc, xml_id, 'ir.actions.server', target_id)
        self._record_item_and_commit(ctx, 'server_action', src_model_name, action['name'], xml_id, res_id=target_id)
        sync_action_id_in_target_views(target_rpc, res_id, xml_id)
        return _("Server Action '%s': migrated successfully.") % xml_id

    def _migrate_server_actions_for_model(self, source_rpc, target_rpc, model_name, rename_map, cache, overwrite=None, ctx=None):
        src_models = source_rpc.search_read('ir.model', [('model', '=', model_name)], ['id'], limit=1)
        if not src_models:
            raise UserError(_("Model '%s' was not found on the source system.") % model_name)
        src_mid = src_models[0]['id']
        actions = source_rpc.search_read(
            'ir.actions.server',
            ['|', ('model_id', '=', src_mid), ('binding_model_id', '=', src_mid)],
            ['id', 'name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type'],
        )
        if not actions:
            return [_("Server actions for model '%s': none found on source.") % model_name]

        messages = []
        for action in actions:
            src_data = source_rpc.search_read(
                'ir.model.data',
                [('model', '=', 'ir.actions.server'), ('res_id', '=', action['id'])],
                ['module', 'name'], limit=1,
            )
            if src_data:
                act_xml_id = f"{src_data[0]['module']}.{src_data[0]['name']}"
                msg = self._migrate_server_action(source_rpc, target_rpc, act_xml_id, rename_map, cache, overwrite=overwrite, ctx=ctx)
                messages.append(msg)
            else:
                msg = self._migrate_one_server_action(source_rpc, target_rpc, action, rename_map, cache, overwrite=overwrite, ctx=ctx)
                messages.append(msg)
        return messages

    def _migrate_one_server_action(self, source_rpc, target_rpc, action, rename_map, cache, overwrite=None, ctx=None):
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        target_xml_id = build_xml_id(target_mod, 'server_action', action['name'])

        src_model_name = self._read_model_name(source_rpc, action.get('model_id'))
        src_binding_model_name = self._read_model_name(source_rpc, action.get('binding_model_id'))

        target_model_id = False
        if src_model_name:
            target_model_id = self._get_target_model_id_strict(target_rpc, src_model_name, rename_map, cache)
        binding_model_id = False
        if src_binding_model_name:
            binding_model_id = self._get_target_model_id_strict(target_rpc, src_binding_model_name, rename_map, cache)

        vals = self._build_server_action_vals(action, target_model_id, binding_model_id)

        target_id = False
        if target_xml_id:
            target_id = self._find_target_by_xml_id(target_rpc, target_xml_id, 'ir.actions.server')
        if not target_id:
            dom = [('name', '=', action['name'])]
            if target_model_id:
                dom.append(('model_id', '=', target_model_id))
            existing = target_rpc.search_read('ir.actions.server', dom, ['id'], limit=1)
            target_id = existing[0]['id'] if existing else False

        should_overwrite = self.on_conflict == 'overwrite' if overwrite is None else overwrite
        if target_id:
            if should_overwrite:
                target_rpc.write('ir.actions.server', [target_id], vals)
                self._create_xml_id(target_rpc, target_xml_id, 'ir.actions.server', target_id)
                self._record_item_and_commit(ctx, 'server_action', src_model_name, action['name'], target_xml_id, res_id=target_id)
                if action.get('id'):
                    sync_action_id_in_target_views(target_rpc, action['id'], target_xml_id)
                return _("Server Action '%s': overwritten.") % action['name']
            return _("Server Action '%s': already exists, skipped.") % action['name']

        target_id = target_rpc.create('ir.actions.server', vals)
        self._create_xml_id(target_rpc, target_xml_id, 'ir.actions.server', target_id)
        self._record_item_and_commit(ctx, 'server_action', src_model_name, action['name'], target_xml_id, res_id=target_id)
        if action.get('id'):
            sync_action_id_in_target_views(target_rpc, action['id'], target_xml_id)
        return _("Server Action '%s': migrated successfully.") % action['name']

    @staticmethod
    def _read_model_name(rpc, many2one_tuple):
        if not many2one_tuple:
            return False
        model_id = many2one_tuple[0] if isinstance(many2one_tuple, (list, tuple)) else many2one_tuple
        rec = rpc.read('ir.model', [model_id], ['model'])
        return rec[0]['model'] if rec else False

    def _migrate_menu_by_xml_id(self, source_rpc, target_rpc, xml_id, rename_map, cache, ctx=None):
        if '.' not in xml_id:
            raise UserError(_("XML ID '%s' is invalid; use the module.name format.") % xml_id)
        module, name = xml_id.split('.', 1)
        src_data = source_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name)],
            ['res_id', 'model'], limit=1,
        )
        if not src_data or src_data[0]['model'] not in ('ir.ui.menu', 'ir.actions.act_window'):
            raise UserError(_("Menu or window action with XML ID '%s' not found on source.") % xml_id)

        messages = []
        if src_data[0]['model'] == 'ir.ui.menu':
            m_items = source_rpc.read(
                'ir.ui.menu', [src_data[0]['res_id']],
                ['id', 'name', 'parent_id', 'sequence', 'active', 'web_icon', 'action'],
            )
            if not m_items:
                return [_("Menu '%s' not found on source.") % xml_id]
            source_menu = m_items[0]
            action_id = False
            if source_menu.get('action') and isinstance(source_menu['action'], str) and source_menu['action'].startswith('ir.actions.act_window,'):
                act_id = int(source_menu['action'].split(',')[1])
                src_acts = source_rpc.read(
                    'ir.actions.act_window', [act_id],
                    ['id', 'name', 'res_model', 'view_mode', 'domain', 'context', 'limit', 'target', 'help'],
                )
                if src_acts:
                    tgt_m = rename_map.get(src_acts[0]['res_model'], src_acts[0]['res_model'])
                    action_id = self._find_or_create_window_action(source_rpc, target_rpc, src_acts[0], tgt_m, cache, ctx=ctx)
                    messages.append(_(" - Window action '%s': migrated successfully.") % src_acts[0]['name'])
            self._find_or_create_menu(source_rpc, target_rpc, source_menu, action_id, cache, ctx=ctx)
            messages.append(_(" - Menu '%s': migrated successfully.") % source_menu['name'])
            return messages
        else:
            # act_window
            src_acts = source_rpc.read(
                'ir.actions.act_window', [src_data[0]['res_id']],
                ['id', 'name', 'res_model', 'view_mode', 'domain', 'context', 'limit', 'target', 'help'],
            )
            if not src_acts:
                return [_("Window action '%s' not found on source.") % xml_id]
            tgt_m = rename_map.get(src_acts[0]['res_model'], src_acts[0]['res_model'])
            action_id = self._find_or_create_window_action(source_rpc, target_rpc, src_acts[0], tgt_m, cache, ctx=ctx)
            messages.append(_(" - Window action '%s': migrated successfully.") % src_acts[0]['name'])
            action_menus = source_rpc.search_read(
                'ir.ui.menu',
                [('action', '=', 'ir.actions.act_window,%s' % src_acts[0]['id'])],
                ['name', 'parent_id', 'sequence', 'active', 'web_icon'],
            )
            for source_menu in action_menus:
                self._find_or_create_menu(source_rpc, target_rpc, source_menu, action_id, cache, ctx=ctx)
                messages.append(_(" - Menu '%s': migrated successfully.") % source_menu['name'])
            return messages

    def _migrate_menus_for_model(self, source_rpc, target_rpc, model_name, target_model_name, cache, ctx=None):
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        messages = []
        actions = source_rpc.search_read(
            'ir.actions.act_window', [('res_model', '=', model_name)], [
                'id', 'name', 'res_model', 'view_mode', 'domain', 'context', 'limit',
                'target', 'help',
            ],
        )
        if not actions:
            # Auto-generate window action and menu item on target
            model_rows = target_rpc.search_read('ir.model', [('model', '=', target_model_name)], ['name'], limit=1)
            action_name = model_rows[0]['name'] if model_rows else target_model_name
            act_xml_id = build_xml_id(target_mod, 'action', action_name, model_name=target_model_name)
            existing_act = None
            if '.' in act_xml_id:
                tgt_m_mod, tgt_m_name = act_xml_id.split('.', 1)
                tgt_data = target_rpc.search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.actions.act_window')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    existing_act = tgt_data[0]['res_id']
            if not existing_act:
                res = target_rpc.search_read(
                    'ir.actions.act_window',
                    [('res_model', '=', target_model_name)],
                    ['id', 'name'], limit=1,
                )
                if res:
                    existing_act = res[0]['id']

            if existing_act:
                action_id = existing_act
            else:
                act_vals = {
                    'name': action_name,
                    'res_model': target_model_name,
                    'view_mode': 'list,form',
                    'target': 'current',
                }
                action_id = target_rpc.create('ir.actions.act_window', act_vals)
                self._create_xml_id(target_rpc, act_xml_id, 'ir.actions.act_window', action_id)
                self._record_item_and_commit(ctx, 'menu', target_model_name, action_name, act_xml_id, res_id=action_id)
                messages.append(_(" - Window action '%s': created automatically.") % action_name)

            act_ref = 'ir.actions.act_window,%s' % action_id
            menu_xml_id = build_xml_id(target_mod, 'menu', action_name)
            existing_menu = None
            if '.' in menu_xml_id:
                tgt_m_mod, tgt_m_name = menu_xml_id.split('.', 1)
                tgt_data = target_rpc.search_read(
                    'ir.model.data',
                    [('module', '=', tgt_m_mod), ('name', '=', tgt_m_name), ('model', '=', 'ir.ui.menu')],
                    ['res_id'], limit=1,
                )
                if tgt_data:
                    existing_menu = tgt_data[0]['res_id']
            if not existing_menu:
                res = target_rpc.search_read(
                    'ir.ui.menu',
                    [('action', '=', act_ref)],
                    ['id'], limit=1,
                )
                if res:
                    existing_menu = res[0]['id']

            if not existing_menu:
                menu_vals = {
                    'name': action_name,
                    'action': act_ref,
                    'sequence': 10,
                    'active': True,
                }
                menu_id = target_rpc.create('ir.ui.menu', menu_vals)
                self._create_xml_id(target_rpc, menu_xml_id, 'ir.ui.menu', menu_id)
                self._record_item_and_commit(ctx, 'menu', False, action_name, menu_xml_id, res_id=menu_id)
                messages.append(_(" - Menu '%s' for model '%s': created automatically.") % (action_name, target_model_name))
            return messages

        for source_action in actions:
            action_id = self._find_or_create_window_action(
                source_rpc, target_rpc, source_action, target_model_name, cache, ctx=ctx,
            )
            action_menus = source_rpc.search_read(
                'ir.ui.menu',
                [('action', '=', 'ir.actions.act_window,%s' % source_action['id'])],
                ['name', 'parent_id', 'sequence', 'active', 'web_icon'],
            )
            if not action_menus:
                messages.append(_(" - Window action '%s': created, no related menu found.") % source_action['name'])
                continue
            for source_menu in action_menus:
                self._find_or_create_menu(
                    source_rpc, target_rpc, source_menu, action_id, cache, ctx=ctx,
                )
                messages.append(_(" - Menu '%s' for model '%s': migrated successfully.") % (source_menu['name'], target_model_name))
        return messages

    # ---------- High-level Step Apply Handlers ----------

    def _apply_model(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        src_rows = ctx['source_rpc'].search_read('ir.model', [('model', '=', m)], ['name', 'model', 'state', 'transient'], limit=1)
        if not src_rows:
            raise UserError(_("Model '%s' was not found on the source system.") % m)
        target_model_id = self._ensure_target_model(ctx['target_rpc'], src_rows[0], tname, ctx['cache'], ctx=ctx)

        mapping = self.env['meta.migration.model.map'].search([
            ('source_connection_id', '=', self.source_connection_id.id),
            ('target_connection_id', '=', self.target_connection_id.id),
            ('source_model', '=', m),
        ], limit=1)
        mapping_vals = {
            'source_connection_id': self.source_connection_id.id,
            'target_connection_id': self.target_connection_id.id,
            'source_model': m,
            'target_model': tname,
        }
        if mapping:
            mapping.write(mapping_vals)
        else:
            self.env['meta.migration.model.map'].create(mapping_vals)

        # Check and apply missing or changed fields for this model if not explicitly listed in separate field steps
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
            source_fields = ctx['source_rpc'].search_read(
                'ir.model.fields',
                [('model', '=', m), ('state', '=', 'manual')],
                ALL_FIELD_KEYS,
            )
            if source_fields:
                pass1 = [f for f in source_fields if f.get('ttype') != 'one2many'] + \
                        [f for f in source_fields if f.get('ttype') == 'one2many']
                for fvals in pass1:
                    self._write_field_pass1(ctx['target_rpc'], target_model_id, tname, fvals, ctx['rename_map'], ctx=ctx)

                for fvals in pass1:
                    logic = {k: fvals.get(k) for k in FIELD_LOGIC_KEYS if fvals.get(k)}
                    if logic:
                        self._write_field_pass2(ctx['target_rpc'], target_model_id, fvals['name'], logic)

        # Apply views if ticked and no explicit view steps
        if step.get('create_list_view') and not has_explicit_view_steps:
            self._migrate_views_for_model(ctx['source_rpc'], ctx['target_rpc'], m, tname, ctx['cache'], vtype='list', ctx=ctx)
        if step.get('create_form_view') and not has_explicit_view_steps:
            self._migrate_views_for_model(ctx['source_rpc'], ctx['target_rpc'], m, tname, ctx['cache'], vtype='form', ctx=ctx)
        if step.get('create_search_view') and not has_explicit_view_steps:
            self._migrate_views_for_model(ctx['source_rpc'], ctx['target_rpc'], m, tname, ctx['cache'], vtype='search', ctx=ctx)

        # Apply access rights if ticked and no explicit access steps
        if step.get('copy_access_rights') and not has_explicit_access_steps:
            self._migrate_access_rights(ctx['source_rpc'], ctx['target_rpc'], m, target_model_id, ctx['cache'], ctx=ctx)

        # Apply record rules if ticked and no explicit rule steps
        if step.get('copy_record_rules') and not has_explicit_rule_steps:
            self._migrate_record_rules(ctx['source_rpc'], ctx['target_rpc'], m, target_model_id, ctx['cache'], ctx=ctx)

        # Apply menus if ticked and no explicit menu steps
        if step.get('create_menu') and not has_explicit_menu_steps:
            self._migrate_menus_for_model(ctx['source_rpc'], ctx['target_rpc'], m, tname, ctx['cache'], ctx=ctx)

        return target_model_id

    def _apply_field_block(self, block, ctx):
        # Gather all field items across the block
        items = []
        for step in block:
            m = step.get('model_name')
            fname = step.get('field_name')
            xml_id = step.get('xml_id')
            tmodel = ctx['rename_map'].get(m, m) if m else ''

            if xml_id:
                if '.' in xml_id:
                    module, name = xml_id.split('.', 1)
                    src_data = ctx['source_rpc'].search_read(
                        'ir.model.data',
                        [('module', '=', module), ('name', '=', name), ('model', '=', 'ir.model.fields')],
                        ['res_id', 'model'], limit=1,
                    )
                    if src_data:
                        fields_data = ctx['source_rpc'].read('ir.model.fields', [src_data[0]['res_id']], ALL_FIELD_KEYS)
                        if fields_data:
                            fvals = fields_data[0]
                            field_m = fvals.get('model') or m
                            field_tmodel = ctx['rename_map'].get(field_m, field_m)
                            items.append({'model_name': field_m, 'tmodel': field_tmodel, 'fvals': fvals, 'xml_id': xml_id})
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
                items.append({'model_name': m, 'tmodel': tmodel, 'fvals': fvals})
            else:
                domain = [('model', '=', m), ('state', '=', 'manual')]
                if fname:
                    domain.append(('name', '=', fname))
                fields_data = ctx['source_rpc'].search_read('ir.model.fields', domain, ALL_FIELD_KEYS)
                for fvals in fields_data:
                    items.append({'model_name': m, 'tmodel': tmodel, 'fvals': fvals})

        # Multi-pass application over the entire block
        pass1 = [it for it in items if it['fvals'].get('ttype') != 'one2many'] + \
                [it for it in items if it['fvals'].get('ttype') == 'one2many']

        for it in pass1:
            tmid = self._get_target_model_id_strict(ctx['target_rpc'], it['model_name'], ctx['rename_map'], ctx['cache'])
            self._write_field_pass1(ctx['target_rpc'], tmid, it['tmodel'], it['fvals'], ctx['rename_map'], ctx=ctx)

        for it in pass1:
            logic = {k: it['fvals'].get(k) for k in FIELD_LOGIC_KEYS if it['fvals'].get(k)}
            if logic:
                tmid = self._get_target_model_id_strict(ctx['target_rpc'], it['model_name'], ctx['rename_map'], ctx['cache'])
                self._write_field_pass2(ctx['target_rpc'], tmid, it['fvals']['name'], logic)

    def _apply_view(self, step, ctx):
        if step.get('action') == 'update' and step.get('arch'):
            return self._apply_view_update(step, ctx)
        return self._apply_view_create(step, ctx)

    def _apply_view_create(self, step, ctx):
        if step.get('xml_id'):
            return self._migrate_view_by_xml_id(ctx['source_rpc'], ctx['target_rpc'], step['xml_id'], ctx['rename_map'], ctx['cache'], ctx=ctx)

        m = step.get('model_name')
        tname = ctx['rename_map'].get(m, m)
        target_mod = (ctx and ctx.get('target_module')) or ((ctx and ctx.get('job') or self.job_id).target_module_name if (ctx and ctx.get('job') or self.job_id) else 'meta_migrator')
        self._get_target_model_id_strict(ctx['target_rpc'], m, ctx['rename_map'], ctx['cache'])
        if step.get('arch'):
            vtype = step.get('view_type') or 'form'
            vname = step.get('view_name') or f"{vtype} view on {tname}"
            arch = replace_action_references_in_arch(step['arch'], ctx['source_rpc'], ctx['target_rpc'], target_mod, ctx['cache'])
            vvals = {
                'name': vname,
                'model': tname,
                'type': vtype,
                'arch': arch,
                'priority': step.get('priority', 16),
            }
            target_xml_id = step.get('xml_id') or build_xml_id(target_mod, 'view', vname, model_name=tname)
            target_id = False
            if target_xml_id:
                target_id = self._find_target_by_xml_id(ctx['target_rpc'], target_xml_id, 'ir.ui.view')
            if not target_id:
                existing = ctx['target_rpc'].search_read(
                    'ir.ui.view',
                    [('model', '=', tname), ('type', '=', vtype), ('name', '=', vname)],
                    ['id'],
                )
                target_id = existing[0]['id'] if existing else False

            if target_id:
                if self.on_conflict == 'overwrite':
                    ctx['target_rpc'].write('ir.ui.view', [target_id], vvals)
                    self._create_xml_id(ctx['target_rpc'], target_xml_id, 'ir.ui.view', target_id)
                    self._record_item_and_commit(ctx, 'view', tname, vname, target_xml_id, res_id=target_id)
                    return _(" - View '%s' for model '%s': overwritten.") % (vtype, tname)
                return _(" - View '%s' for model '%s': already exists, skipped.") % (vtype, tname)

            target_id = ctx['target_rpc'].create('ir.ui.view', vvals)
            self._create_xml_id(ctx['target_rpc'], target_xml_id, 'ir.ui.view', target_id)
            self._record_item_and_commit(ctx, 'view', tname, vname, target_xml_id, res_id=target_id)
            return _(" - View '%s' for model '%s': created successfully.") % (vtype, tname)
        return self._migrate_views_for_model(ctx['source_rpc'], ctx['target_rpc'], m, tname, ctx['cache'], vtype=step.get('view_type'), ctx=ctx)

    def _apply_view_update(self, step, ctx):
        xml_id = step['xml_id']
        module, name = xml_id.split('.', 1)
        src_data = ctx['source_rpc'].search_read('ir.model.data', [('module', '=', module), ('name', '=', name)], ['res_id', 'model'], limit=1)
        if not src_data or src_data[0]['model'] != 'ir.ui.view':
            raise UserError(_("View with XML ID '%s' not found on source.") % xml_id)
        src_view = ctx['source_rpc'].read('ir.ui.view', [src_data[0]['res_id']], ['arch', 'inherit_id', 'model'])[0]

        tgt_data = ctx['target_rpc'].search_read('ir.model.data', [('module', '=', module), ('name', '=', name)], ['res_id', 'model'], limit=1)
        if not tgt_data or tgt_data[0]['model'] != 'ir.ui.view':
            raise UserError(_("View with XML ID '%s' does not exist on target.") % xml_id)
        tgt_view = ctx['target_rpc'].read('ir.ui.view', [tgt_data[0]['res_id']], ['arch', 'inherit_id', 'model'])[0]

        res = view_merge.plan_append(src_view['arch'], tgt_view['arch'], bool(src_view.get('inherit_id')), bool(tgt_view.get('inherit_id')))
        if res.error:
            raise UserError(res.error)
        if res.added:
            ctx['target_rpc'].write('ir.ui.view', [tgt_view['id']], {'arch': res.new_arch})
            self._record_item_and_commit(ctx, 'view', src_view.get('model'), tgt_view.get('name') or xml_id, xml_id, res_id=tgt_view['id'])
            return _("View '%s': appended %d elements.") % (xml_id, len(res.added))
        return _("View '%s': already in sync.") % xml_id

    def _apply_server_action(self, step, ctx):
        if step.get('xml_id'):
            xml_id = step['xml_id']
            if step.get('code') or step.get('action_name'):
                module, name = xml_id.split('.', 1)
                target_model_id = False
                if step.get('model_name'):
                    target_model_id = self._get_target_model_id_strict(
                        ctx['target_rpc'], step['model_name'], ctx['rename_map'], ctx['cache']
                    )
                binding_model_id = False
                if step.get('binding_model'):
                    binding_model_id = self._get_target_model_id_strict(
                        ctx['target_rpc'], step['binding_model'], ctx['rename_map'], ctx['cache']
                    )
                act_name = step.get('action_name') or name
                vals = {
                    'name': act_name,
                    'state': step.get('state') or 'code',
                    'code': step.get('code') or '',
                }
                if target_model_id:
                    vals['model_id'] = target_model_id
                if binding_model_id:
                    vals['binding_model_id'] = binding_model_id
                    vals['binding_type'] = step.get('binding_type') or 'action'

                existing_data = ctx['target_rpc'].search_read(
                    'ir.model.data',
                    [('module', '=', module), ('name', '=', name)],
                    ['res_id'],
                )
                should_overwrite = self.on_conflict == 'overwrite' or step['action'] == 'update'
                if existing_data:
                    target_id = existing_data[0]['res_id']
                    if should_overwrite:
                        ctx['target_rpc'].write('ir.actions.server', [target_id], vals)
                        self._record_item_and_commit(ctx, 'server_action', step.get('model_name'), act_name, xml_id, res_id=target_id)
                        return _("Server Action '%s': overwritten.") % xml_id
                    return _("Server Action '%s': already exists, skipped.") % xml_id

                target_id = ctx['target_rpc'].create('ir.actions.server', vals)
                self._create_xml_id(ctx['target_rpc'], xml_id, 'ir.actions.server', target_id)
                self._record_item_and_commit(ctx, 'server_action', step.get('model_name'), act_name, xml_id, res_id=target_id)
                return _("Server Action '%s': migrated successfully.") % xml_id

            overwrite = True if step['action'] == 'update' else None
            return self._migrate_server_action(ctx['source_rpc'], ctx['target_rpc'], xml_id, ctx['rename_map'], ctx['cache'], overwrite=overwrite, ctx=ctx)

        return self._migrate_server_actions_for_model(
            ctx['source_rpc'], ctx['target_rpc'], step['model_name'],
            ctx['rename_map'], ctx['cache'], overwrite=(step['action'] == 'update' if step.get('action') else None), ctx=ctx
        )

    def _apply_menu(self, step, ctx):
        if step.get('xml_id'):
            return self._migrate_menu_by_xml_id(ctx['source_rpc'], ctx['target_rpc'], step['xml_id'], ctx['rename_map'], ctx['cache'], ctx=ctx)
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        return self._migrate_menus_for_model(ctx['source_rpc'], ctx['target_rpc'], m, tname, ctx['cache'], ctx=ctx)

    def _apply_access_right(self, step, ctx):
        if step.get('xml_id'):
            return self._migrate_access_right_by_xml_id(ctx['source_rpc'], ctx['target_rpc'], step['xml_id'], ctx['rename_map'], ctx['cache'], ctx=ctx)
        m = step['model_name']
        tmid = self._get_target_model_id_strict(ctx['target_rpc'], m, ctx['rename_map'], ctx['cache'])
        return self._migrate_access_rights(ctx['source_rpc'], ctx['target_rpc'], m, tmid, ctx['cache'], ctx=ctx)

    def _apply_record_rule(self, step, ctx):
        if step.get('xml_id'):
            return self._migrate_record_rule_by_xml_id(ctx['source_rpc'], ctx['target_rpc'], step['xml_id'], ctx['rename_map'], ctx['cache'], ctx=ctx)
        m = step['model_name']
        tmid = self._get_target_model_id_strict(ctx['target_rpc'], m, ctx['rename_map'], ctx['cache'])
        return self._migrate_record_rules(ctx['source_rpc'], ctx['target_rpc'], m, tmid, ctx['cache'], ctx=ctx)
