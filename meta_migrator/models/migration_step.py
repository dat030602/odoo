from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

ALLOWED_ACTIONS = {
    'model': {'create'},
    'field': {'create'},
    'view': {'create', 'update'},
    'server_action': {'create', 'update'},
    'menu': {'create'},
    'access_right': {'create'},
    'record_rule': {'create'},
}

REQUIRED_INPUTS = {
    ('model', 'create'): ['model_name'],
    ('field', 'create'): ['model_name'],
    ('view', 'create'): ['model_name', 'view_type'],
    ('view', 'update'): ['xml_id'],
    ('server_action', 'create'): ['xml_id'],
    ('server_action', 'update'): ['xml_id'],
    ('menu', 'create'): ['model_name'],
    ('access_right', 'create'): ['model_name'],
    ('record_rule', 'create'): ['model_name'],
}


class MetaMigrationStep(models.Model):
    _name = 'meta.migration.step'
    _description = 'Migration Step (Meta Migrator)'
    _order = 'job_id, sequence, id'

    job_id = fields.Many2one('meta.migration.job', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10, help="Execution order")
    active = fields.Boolean(default=True, help="Disable step without deleting")

    action = fields.Selection([
        ('create', 'Create'),
        ('update', 'Update'),
    ], default='create', required=True)

    object_type = fields.Selection([
        ('model', 'Model'),
        ('field', 'Field'),
        ('view', 'View'),
        ('server_action', 'Server Action'),
        ('menu', 'Menu'),
        ('access_right', 'Access Right'),
        ('record_rule', 'Record Rule'),
    ], required=True)

    # ==========================================
    # 1. MODEL SETUP (object_type == 'model')
    # ==========================================
    model_name = fields.Char(string='Model Technical Name', help="e.g. sale.order or x_custom_model")
    model_description = fields.Char(string='Model Description / Label', help="e.g. Custom Sale Order or My Model")
    target_model_name = fields.Char(string='Target Model Name', help="Target model name (empty = keep)")
    transient = fields.Boolean(string='Transient Model', default=False)
    # Options for model step (migrating related records or generating definitions)
    create_list_view = fields.Boolean(string='Create List View', default=True)
    create_form_view = fields.Boolean(string='Create Form View', default=True)
    create_search_view = fields.Boolean(string='Create Search View', default=True)
    create_menu = fields.Boolean(string='Create Menu', default=True)
    copy_access_rights = fields.Boolean(string='Copy Access Rights', default=True)
    copy_record_rules = fields.Boolean(string='Copy Record Rules', default=False)

    # ==========================================
    # 2. FIELD SETUP (object_type == 'field')
    # ==========================================
    field_name = fields.Char(string='Field Technical Name', help="e.g. x_custom_field (empty = all manual fields)")
    field_description = fields.Char(string='Field Label')
    ttype = fields.Selection([
        ('boolean', 'Boolean'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('monetary', 'Monetary'),
        ('char', 'Char'),
        ('text', 'Text'),
        ('html', 'HTML'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('binary', 'Binary'),
        ('selection', 'Selection'),
        ('many2one', 'Many2one'),
        ('one2many', 'One2many'),
        ('many2many', 'Many2many'),
    ], string='Field Type')
    relation = fields.Char(string='Related Model / Comodel', help="e.g. res.partner")
    relation_field = fields.Char(string='Relation Field (Inverse)', help="For one2many, e.g. order_id")
    selection = fields.Text(string='Selection Options', help="e.g. [('draft', 'Draft'), ('done', 'Done')]")
    required = fields.Boolean(string='Required', default=False)
    readonly = fields.Boolean(string='Readonly', default=False)
    store = fields.Boolean(string='Stored', default=True)
    index = fields.Boolean(string='Indexed', default=False)
    copied = fields.Boolean(string='Copied', default=True)
    translate = fields.Boolean(string='Translatable', default=False)
    on_delete = fields.Selection([
        ('cascade', 'Cascade'),
        ('set null', 'Set Null'),
        ('restrict', 'Restrict'),
    ], string='On Delete', default='set null')
    help = fields.Text(string='Help Tooltip')
    compute = fields.Text(string='Compute (Python Code)')
    depends = fields.Char(string='Dependencies (comma separated)', help="e.g. partner_id,amount_total")
    related = fields.Char(string='Related Field', help="e.g. partner_id.name")

    # ==========================================
    # 3. VIEW SETUP (object_type == 'view')
    # ==========================================
    view_name = fields.Char(string='View Name')
    view_type = fields.Selection([
        ('list', 'List'),
        ('form', 'Form'),
        ('search', 'Search'),
        ('kanban', 'Kanban'),
        ('qweb', 'QWeb'),
    ], string='View Type')
    priority = fields.Integer(string='Sequence / Priority', default=16)
    xml_id = fields.Char(string='XML ID / External ID', help="e.g. module.view_name")
    inherit_xml_id = fields.Char(string='Inherited View XML ID', help="e.g. sale.view_order_form")
    mode = fields.Selection([
        ('primary', 'Base view'),
        ('extension', 'Extension view'),
    ], string='View Mode', default='primary')
    arch = fields.Text(string='Architecture (XML)')

    # ==========================================
    # 4. SERVER ACTION SETUP (object_type == 'server_action')
    # ==========================================
    action_name = fields.Char(string='Action Name')
    state = fields.Selection([
        ('code', 'Execute Python Code'),
        ('object_create', 'Create a new Record'),
        ('object_write', 'Update the Record'),
        ('multi', 'Execute several actions'),
    ], string='Action Type', default='code')
    code = fields.Text(string='Python Code', default="# action.record or env context code\n")
    binding_model = fields.Char(string='Contextual Action Model', help="e.g. sale.order")
    binding_type = fields.Selection([
        ('action', 'Action Button'),
        ('report', 'Report Button'),
    ], string='Binding Type', default='action')

    # ==========================================
    # 5. ACCESS RIGHT SETUP (object_type == 'access_right')
    # ==========================================
    access_name = fields.Char(string='Access Name', help="e.g. access_x_custom_model_user")
    group_xml_id = fields.Char(string='Group XML ID', help="e.g. base.group_user (empty = all users)")
    perm_read = fields.Boolean(string='Read Access', default=True)
    perm_write = fields.Boolean(string='Write Access', default=False)
    perm_create = fields.Boolean(string='Create Access', default=False)
    perm_unlink = fields.Boolean(string='Delete Access', default=False)

    # ==========================================
    # 6. RECORD RULE SETUP (object_type == 'record_rule')
    # ==========================================
    rule_name = fields.Char(string='Rule Name', help="e.g. Own Records Only")
    domain_force = fields.Text(string='Domain Filter', default="['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]")
    rule_active = fields.Boolean(string='Rule Active', default=True)

    # ==========================================
    # 7. MENU SETUP (object_type == 'menu')
    # ==========================================
    menu_name = fields.Char(string='Menu Name')
    parent_xml_id = fields.Char(string='Parent Menu XML ID', help="e.g. base.menu_custom")
    menu_sequence = fields.Integer(string='Menu Sequence', default=10)

    label = fields.Char(compute='_compute_label', string='Step Label')

    @api.depends(
        'action', 'object_type', 'model_name', 'target_model_name',
        'model_description', 'field_name', 'ttype', 'view_type',
        'view_name', 'xml_id', 'action_name', 'access_name',
        'rule_name', 'menu_name'
    )
    def _compute_label(self):
        for step in self:
            act = step.action or ''
            otype = step.object_type or ''
            m_disp = step.model_name or ''
            if otype == 'model':
                tgt = f" -> {step.target_model_name}" if step.target_model_name and step.target_model_name != step.model_name else ""
                desc = f" ({step.model_description})" if step.model_description else ""
                step.label = f"{act} model {m_disp}{desc}{tgt}"
            elif otype == 'field':
                f_name = step.field_name or '*'
                t = f" [{step.ttype}]" if step.ttype else ""
                step.label = f"{act} field {m_disp}.{f_name}{t}"
            elif otype == 'view':
                if act == 'create':
                    v_t = step.view_type or ''
                    v_n = f" '{step.view_name}'" if step.view_name else ""
                    step.label = f"create view {v_t}{v_n} on {m_disp}"
                else:
                    step.label = f"update view {step.xml_id or step.view_name or m_disp}"
            elif otype == 'server_action':
                sa_name = step.action_name or step.xml_id or ''
                step.label = f"{act} server action {sa_name}"
            elif otype == 'access_right':
                acc_name = step.access_name or f"for {m_disp}"
                step.label = f"{act} access right {acc_name}"
            elif otype == 'record_rule':
                r_name = step.rule_name or f"for {m_disp}"
                step.label = f"{act} record rule {r_name}"
            elif otype == 'menu':
                mn = step.menu_name or f"for {m_disp}"
                step.label = f"{act} menu {mn}"
            else:
                step.label = f"{act} {otype}"

    @api.onchange('object_type')
    def _onchange_object_type(self):
        if self.object_type and self.action not in ALLOWED_ACTIONS.get(self.object_type, set()):
            self.action = 'create'

    @api.onchange('related')
    def _onchange_related(self):
        if self.related:
            self.compute = False
            self.depends = False

    @api.onchange('compute', 'depends')
    def _onchange_compute_depends(self):
        if self.compute or self.depends:
            self.related = False

    @api.constrains('action', 'object_type', 'model_name', 'field_name', 'view_type', 'xml_id')
    def _check_step(self):
        for step in self:
            allowed = ALLOWED_ACTIONS.get(step.object_type, set())
            if step.action not in allowed:
                raise ValidationError(_('Action %s is not allowed for %s.') % (step.action, step.object_type))
            req_fields = REQUIRED_INPUTS.get((step.object_type, step.action), [])
            for fname in req_fields:
                if not step[fname]:
                    raise ValidationError(_('%s is required for %s %s.') % (fname, step.action, step.object_type))
            if step.xml_id and '.' not in step.xml_id.strip():
                raise ValidationError(_('XML ID must use the module.name format (received: %s).') % step.xml_id)

    @api.constrains('object_type', 'compute', 'depends', 'related')
    def _check_compute_depends_related(self):
        for step in self:
            if step.object_type != 'field':
                continue
            compute = (step.compute or '').strip()
            depends = (step.depends or '').strip()
            related = (step.related or '').strip()
            if related:
                if compute or depends:
                    raise ValidationError(_("A field cannot have both 'related' and 'compute' or 'depends'."))
            else:
                if compute and not depends:
                    raise ValidationError(_("Field '%s': If 'compute' is provided, 'depends' is required.") % (step.field_name or step.model_name))
                if depends and not compute:
                    raise ValidationError(_("Field '%s': If 'depends' is provided, 'compute' is required.") % (step.field_name or step.model_name))

    def _to_snapshot(self):
        self.ensure_one()
        return {
            'id': self.id,
            'sequence': self.sequence,
            'action': self.action,
            'object_type': self.object_type,
            'model_name': (self.model_name or '').strip(),
            'model_description': (self.model_description or '').strip(),
            'target_model_name': (self.target_model_name or '').strip(),
            'transient': self.transient,
            'create_list_view': self.create_list_view,
            'create_form_view': self.create_form_view,
            'create_search_view': self.create_search_view,
            'create_menu': self.create_menu,
            'copy_access_rights': self.copy_access_rights,
            'copy_record_rules': self.copy_record_rules,
            'field_name': (self.field_name or '').strip(),
            'field_description': (self.field_description or '').strip(),
            'ttype': self.ttype,
            'relation': (self.relation or '').strip(),
            'relation_field': (self.relation_field or '').strip(),
            'selection': self.selection,
            'required': self.required,
            'readonly': self.readonly,
            'store': self.store,
            'index': self.index,
            'copied': self.copied,
            'translate': self.translate,
            'on_delete': self.on_delete,
            'help': self.help,
            'compute': self.compute,
            'depends': (self.depends or '').strip(),
            'related': (self.related or '').strip(),
            'view_name': (self.view_name or '').strip(),
            'view_type': self.view_type,
            'priority': self.priority,
            'xml_id': (self.xml_id or '').strip(),
            'inherit_xml_id': (self.inherit_xml_id or '').strip(),
            'mode': self.mode,
            'arch': self.arch,
            'action_name': (self.action_name or '').strip(),
            'state': self.state,
            'code': self.code,
            'binding_model': (self.binding_model or '').strip(),
            'binding_type': self.binding_type,
            'access_name': (self.access_name or '').strip(),
            'group_xml_id': (self.group_xml_id or '').strip(),
            'perm_read': self.perm_read,
            'perm_write': self.perm_write,
            'perm_create': self.perm_create,
            'perm_unlink': self.perm_unlink,
            'rule_name': (self.rule_name or '').strip(),
            'domain_force': self.domain_force,
            'rule_active': self.rule_active,
            'menu_name': (self.menu_name or '').strip(),
            'parent_xml_id': (self.parent_xml_id or '').strip(),
            'menu_sequence': self.menu_sequence,
            'label': self.label,
        }
