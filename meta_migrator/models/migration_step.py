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
    ('view', 'create'): ['model_name'],
    ('view', 'update'): ['model_name'],
    ('server_action', 'create'): ['model_name'],
    ('server_action', 'update'): ['model_name'],
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
    field_name = fields.Char(string='Field Technical Name', help="e.g. x_custom_field (empty = all manual fields of model)")

    # ==========================================
    # 3. TECHNICAL XML ID (view, server_action, menu, field, rule, access)
    # ==========================================
    xml_id = fields.Char(string='XML ID / External ID', help="e.g. module.name (if specified, migrates only this specific record)")

    label = fields.Char(compute='_compute_label', string='Step Label')

    @api.depends(
        'action', 'object_type', 'model_name', 'target_model_name',
        'model_description', 'field_name', 'xml_id'
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
                if step.xml_id:
                    step.label = f"{act} field {step.xml_id}"
                elif step.field_name:
                    step.label = f"{act} field {m_disp}.{step.field_name}"
                else:
                    step.label = f"{act} all manual fields for {m_disp}"
            elif otype == 'view':
                if step.xml_id:
                    step.label = f"{act} view {step.xml_id}"
                else:
                    step.label = f"{act} views for {m_disp}"
            elif otype == 'server_action':
                if step.xml_id:
                    step.label = f"{act} server action {step.xml_id}"
                else:
                    step.label = f"{act} server actions for {m_disp}"
            elif otype == 'access_right':
                if step.xml_id:
                    step.label = f"{act} access right {step.xml_id}"
                else:
                    step.label = f"{act} access rights for {m_disp}"
            elif otype == 'record_rule':
                if step.xml_id:
                    step.label = f"{act} record rule {step.xml_id}"
                else:
                    step.label = f"{act} record rules for {m_disp}"
            elif otype == 'menu':
                if step.xml_id:
                    step.label = f"{act} menu {step.xml_id}"
                else:
                    step.label = f"{act} menus for {m_disp}"
            else:
                step.label = f"{act} {otype}"

    @api.onchange('object_type')
    def _onchange_object_type(self):
        if self.object_type and self.action not in ALLOWED_ACTIONS.get(self.object_type, set()):
            self.action = 'create'

    @api.constrains('action', 'object_type', 'model_name', 'field_name', 'xml_id')
    def _check_step(self):
        for step in self:
            allowed = ALLOWED_ACTIONS.get(step.object_type, set())
            if step.action not in allowed:
                raise ValidationError(_('Action %s is not allowed for %s.') % (step.action, step.object_type))
            if not step.model_name and not step.xml_id:
                raise ValidationError(_("Either 'model_name' or 'xml_id' is required for %s.") % step.object_type)
            if step.xml_id and '.' not in step.xml_id.strip():
                raise ValidationError(_('XML ID must use the module.name format (received: %s).') % step.xml_id)

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
            'xml_id': (self.xml_id or '').strip(),
            'label': self.label,
        }
