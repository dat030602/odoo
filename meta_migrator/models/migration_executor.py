import logging
from odoo import api, models, _
from odoo.exceptions import UserError

from .rpc_helper import OdooRPCError
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

    def _ensure_target_model(self, target_rpc, model_info, target_model_name, cache):
        key = ('model', target_model_name)
        if key in cache:
            return cache[key]

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
        cache[key] = target_id
        return target_id

    @staticmethod
    def _sort_fields_pass1(field_vals):
        non_o2m = [f for f in field_vals if f.get('ttype') != 'one2many']
        o2m = [f for f in field_vals if f.get('ttype') == 'one2many']
        return non_o2m + o2m

    def _write_field_pass1(self, target_rpc, target_model_id, target_model_name, fvals, rename_map):
        vals = self._build_field_vals(fvals, rename_map)
        vals.update({
            'model_id': target_model_id,
            'model': target_model_name,
            'state': 'manual',
        })
        existing = target_rpc.search_read(
            'ir.model.fields',
            [('model_id', '=', target_model_id), ('name', '=', fvals['name'])],
            ['id'],
        )
        if existing:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.model.fields', [existing[0]['id']], vals)
        else:
            target_rpc.create('ir.model.fields', vals)

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

    def _find_or_create_window_action(self, source_rpc, target_rpc, source_action, target_model_name, cache):
        source_xml_id = self._get_xml_id(
            source_rpc, 'ir.actions.act_window', source_action['id'], cache,
        )
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
        if source_xml_id:
            target_id = self._find_target_by_xml_id(
                target_rpc, source_xml_id, 'ir.actions.act_window',
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
            if source_xml_id:
                self._create_xml_id(
                    target_rpc, source_xml_id, 'ir.actions.act_window', target_id,
                )
        return target_id

    def _find_or_create_menu(self, source_rpc, target_rpc, source_menu, action_id, cache):
        source_xml_id = self._get_xml_id(
            source_rpc, 'ir.ui.menu', source_menu['id'], cache,
        )
        parent_id = self._find_target_menu_parent(
            source_rpc, target_rpc, source_menu, cache,
        )
        vals = {
            'name': source_menu['name'],
            'parent_id': parent_id or False,
            'sequence': source_menu.get('sequence', 10),
            'active': source_menu.get('active', True),
            'action': 'ir.actions.act_window,%s' % action_id,
        }
        if source_menu.get('web_icon'):
            vals['web_icon'] = source_menu['web_icon']

        target_id = False
        if source_xml_id:
            target_id = self._find_target_by_xml_id(
                target_rpc, source_xml_id, 'ir.ui.menu',
            )
        if not target_id:
            domain = [('name', '=', source_menu['name']), ('action', '=', vals['action'])]
            domain.append(('parent_id', '=', parent_id or False))
            existing = target_rpc.search_read('ir.ui.menu', domain, ['id'], limit=1)
            target_id = existing[0]['id'] if existing else False

        if target_id:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.ui.menu', [target_id], vals)
        else:
            target_id = target_rpc.create('ir.ui.menu', vals)
            if source_xml_id:
                self._create_xml_id(target_rpc, source_xml_id, 'ir.ui.menu', target_id)
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

    def _migrate_access_rights(self, source_rpc, target_rpc, model_name, target_model_id, cache):
        messages = []
        access_records = source_rpc.search_read(
            'ir.model.access', [('model_id.model', '=', model_name)], [
                'name', 'group_id', 'perm_read', 'perm_write',
                'perm_create', 'perm_unlink',
            ],
        )
        for access in access_records:
            source_group = access.get('group_id')
            source_group_id = source_group[0] if source_group else False
            target_group_id = self._map_group_id(
                source_rpc, target_rpc, source_group_id, cache,
            )
            if source_group_id and not target_group_id:
                messages.append(_(" - Access '%s': source group could not be mapped; skipped.") % access['name'])
                continue
            vals = {
                'name': access['name'],
                'model_id': target_model_id,
                'group_id': target_group_id or False,
                'perm_read': access.get('perm_read', False),
                'perm_write': access.get('perm_write', False),
                'perm_create': access.get('perm_create', False),
                'perm_unlink': access.get('perm_unlink', False),
            }
            existing = target_rpc.search_read(
                'ir.model.access', [
                    ('model_id', '=', target_model_id),
                    ('name', '=', access['name']),
                ], ['id'], limit=1,
            )
            if existing and self.on_conflict == 'overwrite':
                target_rpc.write('ir.model.access', [existing[0]['id']], vals)
                messages.append(_(" - Access '%s': overwritten.") % access['name'])
            elif existing:
                messages.append(_(" - Access '%s': already exists, skipped.") % access['name'])
            else:
                target_rpc.create('ir.model.access', vals)
                messages.append(_(" - Access '%s': migrated successfully.") % access['name'])
        return messages

    def _migrate_record_rules(self, source_rpc, target_rpc, model_name, target_model_id, cache):
        messages = []
        rules = source_rpc.search_read(
            'ir.rule', [('model_id.model', '=', model_name)], [
                'name', 'domain_force', 'groups', 'perm_read', 'perm_write',
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
            existing = target_rpc.search_read(
                'ir.rule', [
                    ('model_id', '=', target_model_id),
                    ('name', '=', rule['name']),
                ], ['id'], limit=1,
            )
            if existing and self.on_conflict == 'overwrite':
                target_rpc.write('ir.rule', [existing[0]['id']], vals)
                messages.append(_(" - Rule '%s': overwritten.") % rule['name'])
            elif existing:
                messages.append(_(" - Rule '%s': already exists, skipped.") % rule['name'])
            else:
                target_rpc.create('ir.rule', vals)
                messages.append(_(" - Rule '%s': migrated successfully.") % rule['name'])
        return messages

    def _migrate_view(self, source_rpc, target_rpc, model_name, target_model_name, vtype):
        search_types = [vtype] if vtype != 'list' else ['list', 'tree']
        views = source_rpc.search_read(
            'ir.ui.view',
            [('model', '=', model_name), ('type', 'in', search_types), ('active', '=', True)],
            ['name', 'type', 'arch', 'priority'],
        )
        if not views:
            return _(" - View '%s' for model '%s': not found on source, skipped.") % (vtype, model_name)

        views.sort(key=lambda v: v.get('priority', 16))
        view = views[0]
        vals = self._build_view_vals(view, target_model_name, vtype)

        existing = target_rpc.search_read(
            'ir.ui.view',
            [('model', '=', target_model_name), ('type', '=', vtype), ('name', '=', view['name'])],
            ['id'],
        )
        if existing:
            if self.on_conflict == 'overwrite':
                target_rpc.write('ir.ui.view', [existing[0]['id']], vals)
                return _(" - View '%s' for model '%s': overwritten.") % (vtype, target_model_name)
            return _(" - View '%s' for model '%s': already exists, skipped.") % (vtype, target_model_name)

        target_rpc.create('ir.ui.view', vals)
        return _(" - View '%s' for model '%s': migrated successfully.") % (vtype, target_model_name)

    def _migrate_server_action(self, source_rpc, target_rpc, xml_id, rename_map, cache, overwrite=None):
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
                return _("Server Action '%s': overwritten.") % xml_id
            return _("Server Action '%s': already exists, skipped.") % xml_id

        target_id = target_rpc.create('ir.actions.server', vals)
        target_rpc.create('ir.model.data', {
            'module': module,
            'name': name,
            'model': 'ir.actions.server',
            'res_id': target_id,
            'noupdate': True,
        })
        return _("Server Action '%s': migrated successfully.") % xml_id

    @staticmethod
    def _read_model_name(rpc, many2one_tuple):
        if not many2one_tuple:
            return False
        model_id = many2one_tuple[0]
        rec = rpc.read('ir.model', [model_id], ['model'])
        return rec[0]['model'] if rec else False

    def _migrate_menus_for_model(self, source_rpc, target_rpc, model_name, target_model_name, cache):
        messages = []
        actions = source_rpc.search_read(
            'ir.actions.act_window', [('res_model', '=', model_name)], [
                'name', 'res_model', 'view_mode', 'domain', 'context', 'limit',
                'target', 'help',
            ],
        )
        if not actions:
            return [_("Menus for model '%s': no window action found.") % model_name]

        for source_action in actions:
            action_id = self._find_or_create_window_action(
                source_rpc, target_rpc, source_action, target_model_name, cache,
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
                    source_rpc, target_rpc, source_menu, action_id, cache,
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
        target_model_id = self._ensure_target_model(ctx['target_rpc'], src_rows[0], tname, ctx['cache'])

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
        return target_model_id

    def _apply_field_block(self, block, ctx):
        # Gather all field items across the block
        items = []
        for step in block:
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
            self._write_field_pass1(ctx['target_rpc'], tmid, it['tmodel'], it['fvals'], ctx['rename_map'])

        for it in pass1:
            logic = {k: it['fvals'].get(k) for k in FIELD_LOGIC_KEYS if it['fvals'].get(k)}
            if logic:
                tmid = self._get_target_model_id_strict(ctx['target_rpc'], it['model_name'], ctx['rename_map'], ctx['cache'])
                self._write_field_pass2(ctx['target_rpc'], tmid, it['fvals']['name'], logic)

    def _apply_view(self, step, ctx):
        if step.get('action') == 'update':
            return self._apply_view_update(step, ctx)
        return self._apply_view_create(step, ctx)

    def _apply_view_create(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        self._get_target_model_id_strict(ctx['target_rpc'], m, ctx['rename_map'], ctx['cache'])
        if step.get('arch'):
            vname = step.get('view_name') or f"{step['view_type']} view on {tname}"
            vvals = {
                'name': vname,
                'model': tname,
                'type': step['view_type'],
                'arch': step['arch'],
                'priority': step.get('priority', 16),
            }
            existing = ctx['target_rpc'].search_read(
                'ir.ui.view',
                [('model', '=', tname), ('type', '=', step['view_type']), ('name', '=', vname)],
                ['id'],
            )
            if existing:
                if self.on_conflict == 'overwrite':
                    ctx['target_rpc'].write('ir.ui.view', [existing[0]['id']], vvals)
                    return _(" - View '%s' for model '%s': overwritten.") % (step['view_type'], tname)
                return _(" - View '%s' for model '%s': already exists, skipped.") % (step['view_type'], tname)
            ctx['target_rpc'].create('ir.ui.view', vvals)
            return _(" - View '%s' for model '%s': created successfully.") % (step['view_type'], tname)
        return self._migrate_view(ctx['source_rpc'], ctx['target_rpc'], m, tname, step['view_type'])

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
            return _("View '%s': appended %d elements.") % (xml_id, len(res.added))
        return _("View '%s': already in sync.") % xml_id

    def _apply_server_action(self, step, ctx):
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
            vals = {
                'name': step.get('action_name') or name,
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
                    return _("Server Action '%s': overwritten.") % xml_id
                return _("Server Action '%s': already exists, skipped.") % xml_id

            target_id = ctx['target_rpc'].create('ir.actions.server', vals)
            ctx['target_rpc'].create('ir.model.data', {
                'module': module,
                'name': name,
                'model': 'ir.actions.server',
                'res_id': target_id,
                'noupdate': True,
            })
            return _("Server Action '%s': migrated successfully.") % xml_id

        overwrite = True if step['action'] == 'update' else None
        return self._migrate_server_action(ctx['source_rpc'], ctx['target_rpc'], xml_id, ctx['rename_map'], ctx['cache'], overwrite=overwrite)

    def _apply_menu(self, step, ctx):
        m = step['model_name']
        tname = ctx['rename_map'].get(m, m)
        return self._migrate_menus_for_model(ctx['source_rpc'], ctx['target_rpc'], m, tname, ctx['cache'])

    def _apply_access_right(self, step, ctx):
        m = step['model_name']
        tmid = self._get_target_model_id_strict(ctx['target_rpc'], m, ctx['rename_map'], ctx['cache'])
        if step.get('access_name'):
            target_group_id = False
            if step.get('group_xml_id') and '.' in step['group_xml_id']:
                g_mod, g_name = step['group_xml_id'].split('.', 1)
                gdata = ctx['target_rpc'].search_read('ir.model.data', [('module', '=', g_mod), ('name', '=', g_name)], ['res_id'], limit=1)
                if gdata:
                    target_group_id = gdata[0]['res_id']
            vals = {
                'name': step['access_name'],
                'model_id': tmid,
                'group_id': target_group_id,
                'perm_read': step.get('perm_read', False),
                'perm_write': step.get('perm_write', False),
                'perm_create': step.get('perm_create', False),
                'perm_unlink': step.get('perm_unlink', False),
            }
            existing = ctx['target_rpc'].search_read(
                'ir.model.access',
                [('model_id', '=', tmid), ('name', '=', step['access_name'])],
                ['id'], limit=1,
            )
            if existing:
                if self.on_conflict == 'overwrite':
                    ctx['target_rpc'].write('ir.model.access', [existing[0]['id']], vals)
                    return [_("Access right '%s': overwritten.") % step['access_name']]
                return [_("Access right '%s': already exists, skipped.") % step['access_name']]
            ctx['target_rpc'].create('ir.model.access', vals)
            return [_("Access right '%s': created successfully.") % step['access_name']]

        return self._migrate_access_rights(ctx['source_rpc'], ctx['target_rpc'], m, tmid, ctx['cache'])

    def _apply_record_rule(self, step, ctx):
        m = step['model_name']
        tmid = self._get_target_model_id_strict(ctx['target_rpc'], m, ctx['rename_map'], ctx['cache'])
        if step.get('rule_name'):
            target_group_ids = []
            if step.get('group_xml_id') and '.' in step['group_xml_id']:
                g_mod, g_name = step['group_xml_id'].split('.', 1)
                gdata = ctx['target_rpc'].search_read('ir.model.data', [('module', '=', g_mod), ('name', '=', g_name)], ['res_id'], limit=1)
                if gdata:
                    target_group_ids = [(4, gdata[0]['res_id'])]
            vals = {
                'name': step['rule_name'],
                'model_id': tmid,
                'domain_force': step.get('domain_force') or '',
                'groups': target_group_ids,
                'perm_read': step.get('perm_read', False),
                'perm_write': step.get('perm_write', False),
                'perm_create': step.get('perm_create', False),
                'perm_unlink': step.get('perm_unlink', False),
                'active': step.get('rule_active', True),
            }
            existing = ctx['target_rpc'].search_read(
                'ir.rule',
                [('model_id', '=', tmid), ('name', '=', step['rule_name'])],
                ['id'], limit=1,
            )
            if existing:
                if self.on_conflict == 'overwrite':
                    ctx['target_rpc'].write('ir.rule', [existing[0]['id']], vals)
                    return [_("Record rule '%s': overwritten.") % step['rule_name']]
                return [_("Record rule '%s': already exists, skipped.") % step['rule_name']]
            ctx['target_rpc'].create('ir.rule', vals)
            return [_("Record rule '%s': created successfully.") % step['rule_name']]

        return self._migrate_record_rules(ctx['source_rpc'], ctx['target_rpc'], m, tmid, ctx['cache'])
