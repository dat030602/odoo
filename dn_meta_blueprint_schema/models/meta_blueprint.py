# -*- coding: utf-8 -*-
import xmlrpc.client
from odoo import models, fields, api, exceptions


class MetaBlueprint(models.Model):
    _name = 'meta.blueprint'
    _description = 'Meta Builder Blueprint'

    name = fields.Char(string='Blueprint Name', required=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', string='Status')

    # Deployment configuration
    deploy_target = fields.Selection([
        ('local', 'Current Database (Local)'),
        ('remote', 'Client Database (Remote)')
    ], string='Deploy To', default='local', required=True)

    remote_url = fields.Char(string='Odoo URL', default='https://client-domain.odoo.com')
    remote_db = fields.Char(string='Database Name')
    remote_user = fields.Char(string='Username (Admin)')
    remote_password = fields.Char(string='Password / API Key')

    # Unified schema table combining Models and Fields with drag-and-drop sequence ordering
    schema_ids = fields.One2many('meta.blueprint.schema', 'blueprint_id', string='Schema (Models & Fields)')

    action_ids = fields.One2many('meta.blueprint.action', 'blueprint_id', string='Actions')
    view_ids = fields.One2many('meta.blueprint.view', 'blueprint_id', string='Views')
    access_ids = fields.One2many('meta.blueprint.access', 'blueprint_id', string='Access Rights')

    def action_build(self):
        """Execute the build process following the exact order of schema items."""
        for record in self:
            if record.deploy_target == 'local':
                record._build_local()
            else:
                record._build_remote()

            record.state = 'done'

    def _build_local(self):
        """Build models, fields, actions, views, and access rights in the current database."""
        for record in self:
            model_map = {}

            # 1. PROCESS SCHEMA (MODELS & FIELDS) IN EXACT SEQUENCE ORDER
            for item in record.schema_ids.sorted('sequence'):

                if item.item_type == 'model':
                    existing = self.env['ir.model'].search([('model', '=', item.model_name)], limit=1)
                    if not existing:
                        existing = self.env['ir.model'].create({
                            'name': item.label,
                            'model': item.model_name,
                            'state': 'manual',
                            'transient': item.is_transient,
                        })
                    else:
                        existing.write({
                            'name': item.label,
                            'transient': item.is_transient,
                        })
                    model_map[item.model_name] = existing.id

                elif item.item_type == 'field':
                    model_id = model_map.get(item.model_name)
                    if not model_id:
                        # Fallback: search in DB if model already exists from another module
                        model_record = self.env['ir.model'].search([('model', '=', item.model_name)], limit=1)
                        if not model_record:
                            raise exceptions.UserError(
                                f"Model '{item.model_name}' does not exist yet. "
                                f"Please declare the Model before Field '{item.name}'."
                            )
                        model_id = model_record.id

                    existing_f = self.env['ir.model.fields'].search([
                        ('model_id', '=', model_id), ('name', '=', item.name)
                    ], limit=1)

                    val = {
                        'name': item.name,
                        'field_description': item.label,
                        'ttype': item.ttype,
                        'model_id': model_id,
                        'state': 'manual',
                    }
                    if item.relation:
                        val['relation'] = item.relation
                    if item.relation_field:
                        val['relation_field'] = item.relation_field
                    if item.compute:
                        val['compute'] = item.compute
                    if item.depends:
                        val['depends'] = item.depends
                    if item.related:
                        val['related'] = item.related
                    val['store'] = item.store

                    if existing_f:
                        existing_f.write(val)
                    else:
                        self.env['ir.model.fields'].create(val)

            # 2. PROCESS ACTIONS
            for act in record.action_ids:
                model_id = self.env['ir.model'].search([('model', '=', act.model_name)], limit=1).id
                action_vals = {
                    'name': act.name,
                    'model_id': model_id,
                    'state': act.state,
                    'code': act.code,
                }
                # Auto-map binding model
                if act.binding_model_name:
                    bind_model = self.env['ir.model'].search([('model', '=', act.binding_model_name)], limit=1)
                    if bind_model:
                        action_vals['binding_model_id'] = bind_model.id
                        action_vals['binding_type'] = 'action'

                existing_act = self.env.ref(act.xmlid, raise_if_not_found=False)
                if existing_act:
                    existing_act.write(action_vals)
                else:
                    new_act = self.env['ir.actions.server'].create(action_vals)
                    self._register_xmlid(act.xmlid, 'ir.actions.server', new_act.id)

            # 3. PROCESS VIEWS
            for vw in record.view_ids:
                # Handle arch_resolve: replace placeholders with resolved DB IDs
                arch_str = vw.arch
                if vw.arch_resolve:
                    resolve_dict = eval(vw.arch_resolve)  # dict like {'key': 'module.action_xmlid'}
                    for key, ref_xmlid in resolve_dict.items():
                        ref_rec = self.env.ref(ref_xmlid)
                        arch_str = arch_str.replace('{' + key + '}', str(ref_rec.id))

                view_vals = {
                    'name': vw.name,
                    'model': vw.model_name,
                    'arch': arch_str,
                }
                existing_vw = self.env.ref(vw.xmlid, raise_if_not_found=False)
                if existing_vw:
                    existing_vw.write(view_vals)
                else:
                    new_vw = self.env['ir.ui.view'].create(view_vals)
                    self._register_xmlid(vw.xmlid, 'ir.ui.view', new_vw.id)

            # 4. PROCESS ACCESS RIGHTS
            for acc in record.access_ids:
                model_id = self.env['ir.model'].search([('model', '=', acc.model_name)], limit=1).id
                group_id = self.env.ref(acc.group_xmlid).id if acc.group_xmlid else False

                existing_acc = self.env['ir.model.access'].search([
                    ('name', '=', acc.name), ('model_id', '=', model_id)
                ], limit=1)

                acc_vals = {
                    'name': acc.name,
                    'model_id': model_id,
                    'group_id': group_id,
                    'perm_read': acc.perm_read,
                    'perm_write': acc.perm_write,
                    'perm_create': acc.perm_create,
                    'perm_unlink': acc.perm_unlink,
                }
                if existing_acc:
                    existing_acc.write(acc_vals)
                else:
                    self.env['ir.model.access'].create(acc_vals)

    def _build_remote(self):
        """Build models, fields, actions, views, and access rights via XML-RPC on a remote Odoo server."""
        self.ensure_one()

        # 1. Connect and authenticate
        try:
            common = xmlrpc.client.ServerProxy(f'{self.remote_url}/xmlrpc/2/common')
            uid = common.authenticate(self.remote_db, self.remote_user, self.remote_password, {})
            if not uid:
                raise exceptions.UserError(
                    "Authentication to the remote server failed! "
                    "Please check User/Password/Database."
                )

            models_rpc = xmlrpc.client.ServerProxy(f'{self.remote_url}/xmlrpc/2/object')
        except Exception as e:
            raise exceptions.UserError(f"Cannot connect to remote server: {str(e)}")

        # Helper function for concise RPC calls
        def rpc_call(model, method, args, kwargs=None):
            if kwargs is None:
                kwargs = {}
            return models_rpc.execute_kw(
                self.remote_db, uid, self.remote_password, model, method, args, kwargs
            )

        model_map = {}

        # 2. PROCESS SCHEMA (MODELS & FIELDS) REMOTELY
        for item in self.schema_ids.sorted('sequence'):
            if item.item_type == 'model':
                existing = rpc_call('ir.model', 'search', [[('model', '=', item.model_name)]], {'limit': 1})
                if not existing:
                    new_id = rpc_call('ir.model', 'create', [{
                        'name': item.label,
                        'model': item.model_name,
                        'state': 'manual',
                        'transient': item.is_transient,
                    }])
                    model_map[item.model_name] = new_id
                else:
                    rpc_call('ir.model', 'write', [existing, {'name': item.label, 'transient': item.is_transient}])
                    model_map[item.model_name] = existing[0]

            elif item.item_type == 'field':
                model_id = model_map.get(item.model_name)
                if not model_id:
                    model_record = rpc_call('ir.model', 'search', [[('model', '=', item.model_name)]], {'limit': 1})
                    if not model_record:
                        raise exceptions.UserError(
                            f"Model '{item.model_name}' does not exist on the remote server. "
                            f"Please declare the Model before Field '{item.name}'."
                        )
                    model_id = model_record[0]

                existing_f = rpc_call('ir.model.fields', 'search', [
                    [('model_id', '=', model_id), ('name', '=', item.name)]
                ], {'limit': 1})

                val = {
                    'name': item.name,
                    'field_description': item.label,
                    'ttype': item.ttype,
                    'model_id': model_id,
                    'state': 'manual',
                    'store': item.store,
                }
                if item.relation:
                    val['relation'] = item.relation
                if item.relation_field:
                    val['relation_field'] = item.relation_field
                if item.compute:
                    val['compute'] = item.compute
                if item.depends:
                    val['depends'] = item.depends
                if item.related:
                    val['related'] = item.related

                if existing_f:
                    rpc_call('ir.model.fields', 'write', [existing_f, val])
                else:
                    rpc_call('ir.model.fields', 'create', [val])

        # 3. PROCESS ACTIONS REMOTELY
        for act in self.action_ids:
            model_id = rpc_call('ir.model', 'search', [[('model', '=', act.model_name)]], {'limit': 1})
            if not model_id:
                raise exceptions.UserError(f"Model '{act.model_name}' not found on remote server.")
            model_id = model_id[0]

            action_vals = {
                'name': act.name,
                'model_id': model_id,
                'state': act.state,
                'code': act.code,
            }
            if act.binding_model_name:
                bind_model = rpc_call('ir.model', 'search', [[('model', '=', act.binding_model_name)]], {'limit': 1})
                if bind_model:
                    action_vals['binding_model_id'] = bind_model[0]
                    action_vals['binding_type'] = 'action'

            existing_act = rpc_call('ir.model.data', 'search_read', [
                [[('module', '=', act.xmlid.split('.')[0]), ('name', '=', act.xmlid.split('.')[1])]]
            ], {'fields': ['res_id'], 'limit': 1})

            if existing_act:
                rpc_call('ir.actions.server', 'write', [[existing_act[0]['res_id']], action_vals])
            else:
                new_act = rpc_call('ir.actions.server', 'create', [action_vals])
                rpc_call('ir.model.data', 'create', [{
                    'module': act.xmlid.split('.')[0],
                    'name': act.xmlid.split('.')[1],
                    'model': 'ir.actions.server',
                    'res_id': new_act,
                    'noupdate': True,
                }])

        # 4. PROCESS VIEWS REMOTELY
        for vw in self.view_ids:
            # Handle arch_resolve: replace placeholders with resolved DB IDs
            arch_str = vw.arch
            if vw.arch_resolve:
                resolve_dict = eval(vw.arch_resolve)
                for key, ref_xmlid in resolve_dict.items():
                    ref_rec = rpc_call('ir.model.data', 'search_read', [
                        [[('module', '=', ref_xmlid.split('.')[0]), ('name', '=', ref_xmlid.split('.')[1])]]
                    ], {'fields': ['res_id'], 'limit': 1})
                    if ref_rec:
                        arch_str = arch_str.replace('{' + key + '}', str(ref_rec[0]['res_id']))

            view_vals = {
                'name': vw.name,
                'model': vw.model_name,
                'arch': arch_str,
            }

            existing_vw = rpc_call('ir.model.data', 'search_read', [
                [[('module', '=', vw.xmlid.split('.')[0]), ('name', '=', vw.xmlid.split('.')[1])]]
            ], {'fields': ['res_id'], 'limit': 1})

            if existing_vw:
                rpc_call('ir.ui.view', 'write', [[existing_vw[0]['res_id']], view_vals])
            else:
                new_vw = rpc_call('ir.ui.view', 'create', [view_vals])
                rpc_call('ir.model.data', 'create', [{
                    'module': vw.xmlid.split('.')[0],
                    'name': vw.xmlid.split('.')[1],
                    'model': 'ir.ui.view',
                    'res_id': new_vw,
                    'noupdate': True,
                }])

        # 5. PROCESS ACCESS RIGHTS REMOTELY
        for acc in self.access_ids:
            model_id = rpc_call('ir.model', 'search', [[('model', '=', acc.model_name)]], {'limit': 1})
            if not model_id:
                raise exceptions.UserError(f"Model '{acc.model_name}' not found on remote server.")
            model_id = model_id[0]

            group_id = False
            if acc.group_xmlid:
                group_rec = rpc_call('ir.model.data', 'search_read', [
                    [[('module', '=', acc.group_xmlid.split('.')[0]), ('name', '=', acc.group_xmlid.split('.')[1])]]
                ], {'fields': ['res_id'], 'limit': 1})
                if group_rec:
                    group_id = group_rec[0]['res_id']

            existing_acc = rpc_call('ir.model.access', 'search', [
                [('name', '=', acc.name), ('model_id', '=', model_id)]
            ], {'limit': 1})

            acc_vals = {
                'name': acc.name,
                'model_id': model_id,
                'group_id': group_id,
                'perm_read': acc.perm_read,
                'perm_write': acc.perm_write,
                'perm_create': acc.perm_create,
                'perm_unlink': acc.perm_unlink,
            }
            if existing_acc:
                rpc_call('ir.model.access', 'write', [existing_acc, acc_vals])
            else:
                rpc_call('ir.model.access', 'create', [acc_vals])

    def _register_xmlid(self, xmlid, model, res_id):
        """Register an XML ID for a created record."""
        if not xmlid or '.' not in xmlid:
            return
        module, name = xmlid.split('.', 1)
        if not self.env['ir.model.data'].search([('module', '=', module), ('name', '=', name)]):
            self.env['ir.model.data'].create({
                'module': module,
                'name': name,
                'model': model,
                'res_id': res_id,
                'noupdate': True,
            })

    def action_reset_to_draft(self):
        """Reset blueprint state to draft."""
        for record in self:
            record.state = 'draft'
