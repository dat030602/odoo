# ============================================================
# META MIGRATOR - MIGRATION JOB
#
# One job = one run, using reusable source and target connection records.
#   - Type: 'model_only' (migrate models and fields, with security options)
#           or 'content' (independently migrate fields, views, and server actions)
#
# Fields are processed in two passes to avoid dependency errors:
#   Pass 1: create or update core properties (ttype, relation, required, and so on)
#   Pass 2: update compute, depends, and related after all model fields exist
# ============================================================

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .rpc_helper import OdooRPCError

_logger = logging.getLogger(__name__)

# Core field properties written in pass 1.
FIELD_CORE_KEYS = [
    'name', 'field_description', 'ttype', 'required', 'readonly',
    'store', 'index', 'copied', 'help', 'relation', 'relation_field',
    'on_delete', 'domain', 'selection', 'translate',
]
# Field logic written separately in pass 2.
FIELD_LOGIC_KEYS = ['compute', 'depends', 'related']

ALL_FIELD_KEYS = FIELD_CORE_KEYS + FIELD_LOGIC_KEYS


class MetaMigrationJob(models.Model):
    _name = 'meta.migration.job'
    _description = 'Meta Migrator Job'
    _order = 'id desc'

    name = fields.Char(required=True, default=lambda self: _('New Migration'))
    source_connection_id = fields.Many2one(
        'meta.migration.connection', string='Source Connection', required=True,
    )
    target_connection_id = fields.Many2one(
        'meta.migration.connection', string='Target Connection', required=True,
    )
    migration_type = fields.Selection([
        ('model_only', 'Model Only'),
        ('content', 'Field / View / Server Action'),
    ], default='model_only', required=True)

    on_conflict = fields.Selection([
        ('skip', 'Skip if already exists'),
        ('overwrite', 'Overwrite if already exists'),
    ], default='skip', required=True)

    # Content options copy the source records instead of generating new definitions.
    do_field = fields.Boolean(string='Fields')
    do_view = fields.Boolean(string='Views')
    do_server_action = fields.Boolean(string='Server Actions')
    create_list_view = fields.Boolean(string='List View')
    create_form_view = fields.Boolean(string='Form View')
    create_search_view = fields.Boolean(string='Search View')
    create_menu = fields.Boolean(string='Create Menus')
    copy_access_rights = fields.Boolean(string='Access Rights')
    copy_record_rules = fields.Boolean(string='Record Rules')

    model_line_ids = fields.One2many('meta.migration.model.line', 'job_id', string='Models')
    field_line_ids = fields.One2many('meta.migration.field.line', 'job_id', string='Fields')
    view_line_ids = fields.One2many('meta.migration.view.line', 'job_id', string='Views')
    menu_line_ids = fields.One2many('meta.migration.menu.line', 'job_id', string='Menus')
    action_line_ids = fields.One2many('meta.migration.action.line', 'job_id', string='Server Actions')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', readonly=True)
    log_text = fields.Text(string='Log', readonly=True)

    # ------------------------------------------------------------
    # ENTRY POINT
    # ------------------------------------------------------------

    def action_run(self):
        for job in self:
            job._run()
        return True

    def _run(self):
        self.ensure_one()
        if not self.source_connection_id or not self.target_connection_id:
            raise UserError(_("Please select both a source and a target connection."))

        source_rpc = self.source_connection_id._get_rpc()
        target_rpc = self.target_connection_id._get_rpc()
        cache = {}
        log_lines = []

        if self.migration_type == 'model_only':
            if not self.model_line_ids:
                raise UserError(_("No models have been entered for migration."))

            # Map source model names to target names so relations are updated
            # for the current model and for related models in this job.
            rename_map = {}
            for line in self.model_line_ids:
                src_name = (line.model_name or '').strip()
                if not src_name:
                    continue
                rename_map[src_name] = (line.target_model_name or src_name).strip()

            for line in self.model_line_ids:
                model_name = (line.model_name or '').strip()
                if not model_name:
                    continue
                target_model_name = rename_map[model_name]
                try:
                    msgs = self._migrate_model(
                        source_rpc, target_rpc, model_name, target_model_name,
                        rename_map, cache,
                    )
                    line.write({'state': 'done', 'message': '\n'.join(msgs)})
                    log_lines.extend(msgs)
                    if self.create_menu:
                        menu_msgs = self._migrate_menus_for_model(
                            source_rpc, target_rpc, model_name, target_model_name, cache,
                        )
                        line.write({'message': '%s\n%s' % (line.message or '', '\n'.join(menu_msgs))})
                        log_lines.extend(menu_msgs)
                except Exception as e:
                    _logger.exception("Migrate model %s failed", model_name)
                    line.write({'state': 'error', 'message': str(e)})
                    log_lines.append(_("Model '%s': ERROR: %s") % (model_name, e))
        else:
            rename_map = self._load_model_map(cache)
            if self.do_field:
                if not self.field_line_ids:
                    raise UserError(_("Fields are enabled, but no field lines have been entered."))
                for line in self.field_line_ids:
                    model_name = (line.model_name or '').strip()
                    field_name = (line.field_name or '').strip()
                    if not model_name or not field_name:
                        continue
                    try:
                        msg = self._migrate_single_field(
                            source_rpc, target_rpc, model_name, field_name,
                            rename_map, cache,
                        )
                        line.write({'state': 'done', 'message': msg})
                        log_lines.append(msg)
                    except Exception as e:
                        _logger.exception("Migrate field %s.%s failed", model_name, field_name)
                        line.write({'state': 'error', 'message': str(e)})
                        log_lines.append(_("Field '%s.%s': ERROR: %s") % (model_name, field_name, e))

            if self.do_view:
                if not self.view_line_ids:
                    raise UserError(_("Views are enabled, but no view lines have been entered."))
                for line in self.view_line_ids:
                    model_name = (line.model_name or '').strip()
                    if not model_name:
                        continue
                    try:
                        msgs = self._migrate_views_for_content(
                            source_rpc, target_rpc, model_name, rename_map, cache,
                        )
                        line.write({'state': 'done', 'message': '\n'.join(msgs)})
                        log_lines.extend(msgs)
                    except Exception as e:
                        _logger.exception("Migrate views for %s failed", model_name)
                        line.write({'state': 'error', 'message': str(e)})
                        log_lines.append(_("Views for '%s': ERROR: %s") % (model_name, e))

            if self.create_menu:
                if not self.menu_line_ids:
                    raise UserError(_("Menus are enabled, but no menu lines have been entered."))
                for line in self.menu_line_ids:
                    model_name = (line.model_name or '').strip()
                    if not model_name:
                        continue
                    try:
                        msgs = self._migrate_menus_for_model(
                            source_rpc, target_rpc, model_name,
                            rename_map.get(model_name, model_name), cache,
                        )
                        line.write({'state': 'done', 'message': '\n'.join(msgs)})
                        log_lines.extend(msgs)
                    except Exception as e:
                        _logger.exception("Migrate menus for %s failed", model_name)
                        line.write({'state': 'error', 'message': str(e)})
                        log_lines.append(_("Menus for '%s': ERROR: %s") % (model_name, e))

            if self.do_server_action:
                if not self.action_line_ids:
                    raise UserError(_("Server Actions are enabled, but no action lines have been entered."))
                for line in self.action_line_ids:
                    xml_id = (line.xml_id or '').strip()
                    if not xml_id:
                        continue
                    try:
                        msg = self._migrate_server_action(
                            source_rpc, target_rpc, xml_id, rename_map, cache,
                        )
                        line.write({'state': 'done', 'message': msg})
                        log_lines.append(msg)
                    except Exception as e:
                        _logger.exception("Migrate action %s failed", xml_id)
                        line.write({'state': 'error', 'message': str(e)})
                        log_lines.append(_("Action '%s': ERROR: %s") % (xml_id, e))

        self.write({'state': 'done', 'log_text': '\n'.join(log_lines)})

    # ------------------------------------------------------------
    # MODEL + FIELD (+ VIEW) MIGRATION
    # ------------------------------------------------------------

    def _migrate_model(self, source_rpc, target_rpc, model_name, target_model_name,
                        rename_map, cache):
        msgs = []

        model_infos = source_rpc.search_read(
            'ir.model', [('model', '=', model_name)],
            ['name', 'model', 'state', 'transient'],
        )
        if not model_infos:
            raise UserError(_("Model '%s' was not found on the source system.") % model_name)
        model_info = model_infos[0]

        target_model_id = self._ensure_target_model(target_rpc, model_info, target_model_name, cache)
        mapping = self.env['meta.migration.model.map'].search([
            ('source_connection_id', '=', self.source_connection_id.id),
            ('target_connection_id', '=', self.target_connection_id.id),
            ('source_model', '=', model_name),
        ], limit=1)
        mapping_vals = {
            'source_connection_id': self.source_connection_id.id,
            'target_connection_id': self.target_connection_id.id,
            'source_model': model_name,
            'target_model': target_model_name,
        }
        if mapping:
            mapping.write(mapping_vals)
        else:
            self.env['meta.migration.model.map'].create(mapping_vals)
        if target_model_name != model_name:
            msgs.append(_("Model '%s' -> '%s': OK (target id=%s)") % (
                model_name, target_model_name, target_model_id))
        else:
            msgs.append(_("Model '%s': OK (target id=%s)") % (model_name, target_model_id))

        source_fields = source_rpc.search_read(
            'ir.model.fields',
            [('model', '=', model_name), ('state', '=', 'manual')],
            ALL_FIELD_KEYS,
        )
        if not source_fields:
            msgs.append(_(" - No custom fields (state=manual) found to copy."))

        sorted_fields = self._sort_fields_pass1(source_fields)

        # ---------- PASS 1: core properties ----------
        for fvals in sorted_fields:
            try:
                self._write_field_pass1(
                    target_rpc, target_model_id, target_model_name, fvals, rename_map,
                )
                msgs.append(_(" - Field '%s': pass 1 OK") % fvals['name'])
            except OdooRPCError as e:
                msgs.append(_(" - Field '%s': pass 1 ERROR: %s") % (fvals['name'], e))

        # ---------- PASS 2: compute / depends / related ----------
        for fvals in sorted_fields:
            logic_vals = {k: fvals.get(k) for k in FIELD_LOGIC_KEYS if fvals.get(k)}
            if not logic_vals:
                continue
            try:
                self._write_field_pass2(target_rpc, target_model_id, fvals['name'], logic_vals)
                msgs.append(_(" - Field '%s': pass 2 (compute/depends/related) OK") % fvals['name'])
            except OdooRPCError as e:
                msgs.append(_(" - Field '%s': pass 2 ERROR: %s") % (fvals['name'], e))

        if self.copy_access_rights:
            msgs.extend(self._migrate_access_rights(
                source_rpc, target_rpc, model_name, target_model_id, cache,
            ))
        if self.copy_record_rules:
            msgs.extend(self._migrate_record_rules(
                source_rpc, target_rpc, model_name, target_model_id, cache,
            ))

        return msgs

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
                      "Run a 'Model Only' job first.") % target_model_name
                )
            cache[key] = existing[0]['id']
        return cache[key]

    def _migrate_single_field(self, source_rpc, target_rpc, model_name, field_name,
                              rename_map, cache):
        model_infos = source_rpc.search_read(
            'ir.model', [('model', '=', model_name)],
            ['name', 'model', 'state', 'transient'], limit=1,
        )
        if not model_infos:
            raise UserError(_("Model '%s' was not found on the source system.") % model_name)
        target_model_name = rename_map.get(model_name, model_name)
        target_model_id = self._get_target_model_id_strict(
            target_rpc, model_name, rename_map, cache,
        )
        source_fields = source_rpc.search_read(
            'ir.model.fields', [
                ('model', '=', model_name),
                ('name', '=', field_name),
                ('state', '=', 'manual'),
            ], ALL_FIELD_KEYS, limit=1,
        )
        if not source_fields:
            raise UserError(
                _("Field '%s.%s' was not found or is not a custom field (state=manual).")
                % (model_name, field_name)
            )
        fvals = source_fields[0]
        self._write_field_pass1(
            target_rpc, target_model_id, target_model_name, fvals, rename_map,
        )
        logic_vals = {key: fvals.get(key) for key in FIELD_LOGIC_KEYS if fvals.get(key)}
        if logic_vals:
            self._write_field_pass2(target_rpc, target_model_id, field_name, logic_vals)
        return _("Field '%s.%s': migrated successfully.") % (model_name, field_name)

    def _migrate_views_for_content(self, source_rpc, target_rpc, model_name,
                                   rename_map, cache):
        self._get_target_model_id_strict(target_rpc, model_name, rename_map, cache)
        target_model_name = rename_map.get(model_name, model_name)
        view_types = []
        if self.create_list_view:
            view_types.append('list')
        if self.create_form_view:
            view_types.append('form')
        if self.create_search_view:
            view_types.append('search')
        if not view_types:
            return [_('Views are enabled, but no view type is selected for model %s.') % model_name]
        return [self._migrate_view(
            source_rpc, target_rpc, model_name, target_model_name, vtype,
        ) for vtype in view_types]

    def _migrate_menus_for_model(self, source_rpc, target_rpc, model_name,
                                 target_model_name, cache):
        messages = []
        actions = source_rpc.search_read(
            'ir.actions.act_window', [('res_model', '=', model_name)], [
                'name', 'res_model', 'view_mode', 'domain', 'context', 'limit',
                'target', 'help',
            ],
        )
        if not actions:
            return [_(
                "Menus for model '%s': no window action found."
            ) % model_name]

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
                messages.append(_(
                    " - Window action '%s': created, no related menu found."
                ) % source_action['name'])
                continue
            for source_menu in action_menus:
                self._find_or_create_menu(
                    source_rpc, target_rpc, source_menu, action_id, cache,
                )
                messages.append(_(
                    " - Menu '%s' for model '%s': migrated successfully."
                ) % (source_menu['name'], target_model_name))
        return messages

    def _find_or_create_window_action(self, source_rpc, target_rpc, source_action,
                                      target_model_name, cache):
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
        """Create one2many fields last so their relation_field exists first."""
        non_o2m = [f for f in field_vals if f.get('ttype') != 'one2many']
        o2m = [f for f in field_vals if f.get('ttype') == 'one2many']
        return non_o2m + o2m

    def _write_field_pass1(self, target_rpc, target_model_id, target_model_name, fvals, rename_map):
        vals = {}
        for k in FIELD_CORE_KEYS:
            v = fvals.get(k)
            if v not in (False, None, ''):
                vals[k] = v
        # Pass store explicitly because ir.model.fields defaults it to True.
        vals['store'] = fvals.get('store', True)

        # Update relational field targets when the related source model was renamed.
        if fvals.get('ttype') in ('many2one', 'one2many', 'many2many') and vals.get('relation'):
            vals['relation'] = rename_map.get(vals['relation'], vals['relation'])

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

    def _migrate_access_rights(self, source_rpc, target_rpc, model_name,
                               target_model_id, cache):
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
                messages.append(_(
                    " - Access '%s': source group could not be mapped; skipped."
                ) % access['name'])
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

    def _migrate_record_rules(self, source_rpc, target_rpc, model_name,
                              target_model_id, cache):
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
                    messages.append(_(
                        " - Rule '%s': a group could not be mapped; continuing without it."
                    ) % rule['name'])

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

        # Find the view on the source by its original model name.
        views = source_rpc.search_read(
            'ir.ui.view',
            [('model', '=', model_name), ('type', 'in', search_types), ('active', '=', True)],
            ['name', 'type', 'arch', 'priority'],
        )
        if not views:
            return _(" - View '%s' for model '%s': not found on source, skipped.") % (vtype, model_name)

        views.sort(key=lambda v: v.get('priority', 16))
        view = views[0]

        # Create or update it on the target using the target model name.
        vals = {
            'name': view['name'],
            'model': target_model_name,
            'type': vtype,
            'arch': view['arch'],
            'priority': view.get('priority', 16),
        }

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

    # ------------------------------------------------------------
    # SERVER ACTION MIGRATION (by XML ID)
    # ------------------------------------------------------------

    def _migrate_server_action(self, source_rpc, target_rpc, xml_id, rename_map, cache):
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

        vals = {
            'name': action['name'],
            'state': action.get('state') or 'code',
            'code': action.get('code'),
        }
        if src_model_name:
            vals['model_id'] = self._get_target_model_id_strict(
                target_rpc, src_model_name, rename_map, cache,
            )
        if src_binding_model_name:
            binding_model_id = self._get_target_model_id_strict(
                target_rpc, src_binding_model_name, rename_map, cache,
            )
            if binding_model_id:
                vals['binding_model_id'] = binding_model_id
                vals['binding_type'] = action.get('binding_type') or 'action'

        existing_data = target_rpc.search_read(
            'ir.model.data',
            [('module', '=', module), ('name', '=', name)],
            ['res_id'],
        )
        if existing_data:
            target_id = existing_data[0]['res_id']
            if self.on_conflict == 'overwrite':
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
        """many2one_tuple từ XML-RPC dạng [id, display_name] -> lấy technical name."""
        if not many2one_tuple:
            return False
        model_id = many2one_tuple[0]
        rec = rpc.read('ir.model', [model_id], ['model'])
        return rec[0]['model'] if rec else False
