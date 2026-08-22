import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ExcelReportDefinition(models.Model):
    _name = 'excel.report.definition'
    _description = 'Excel Report Definition'
    _order = 'name'

    name = fields.Char(required=True)

    target_model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        help='Select an existing model or create a new transient one.',
    )
    target_model_is_new = fields.Boolean(
        compute='_compute_target_model_is_new',
        store=True,
        help='True when the target model is created by this definition.',
    )
    new_model_name = fields.Char(string='New Model Display Name')
    new_model_technical_name = fields.Char(
        string='New Model Technical Name',
        help='Example: x_report_sale_filter. The prefix x_ is added automatically if needed.',
    )

    field_ids = fields.One2many(
        'excel.report.definition.field',
        'definition_id',
        string='Fields',
    )

    server_action_id = fields.Many2one(
        'ir.actions.server',
        string='Server Action',
        domain=[('state', '=', 'excel_template')],
        help='Select an existing Excel template server action.',
    )
    code = fields.Text(
        related='server_action_id.code',
        help='Edit the linked server action code directly.',
    )

    trigger_type = fields.Selection(
        [('menu', 'Menu'), ('contextual', 'Contextual Action')],
        default='menu',
        required=True,
    )
    menu_id = fields.Many2one('ir.ui.menu', readonly=True, copy=False)
    generated_view_id = fields.Many2one('ir.ui.view', readonly=True, copy=False)
    
    can_create_new_model = fields.Boolean(
        compute='_compute_can_create_new_model',
        help='Indicates whether the user can create a new model.',
    )

    @api.depends('target_model_id')
    def _compute_can_create_new_model(self):
        for record in self:
            record.can_create_new_model = not record.target_model_id and self.env.user.has_group('base.group_system')
    
    can_create_new_fields = fields.Boolean(
        compute='_compute_can_create_new_fields',
        help='Indicates whether the user can create new fields on the target model.',
    )

    @api.depends('target_model_id', 'field_ids.field_id')
    def _compute_can_create_new_fields(self):
        for record in self:
            access_model = self.env['ir.model'].check_access_rights('write', raise_exception=False)
            access_field = self.env['ir.model.fields'].check_access_rights('create', raise_exception=False)
            if not record.target_model_id or not access_model or not access_field:
                record.can_create_new_fields = False
                continue
            if len([field for field in record.field_ids if not field.field_id]) > 0:
                record.can_create_new_fields = True

    @api.depends('target_model_id')
    def _compute_target_model_is_new(self):
        for record in self:
            if record.target_model_id:
                record.target_model_is_new = True
            else:
                record.target_model_is_new = False

    @api.constrains('target_model_id', 'new_model_technical_name')
    def _check_target_model(self):
        for record in self:
            if not record.target_model_id and not record.new_model_technical_name:
                raise ValidationError(_(
                    'Select an existing model or provide the technical name for a new one.'
                ))
    
    def action_create_model(self):
        self.ensure_one()
        if not self.can_create_new_model:
            raise UserError(_('You do not have permission to create a new model.'))
        self._ensure_target_model()

    def action_create_fields(self):
        self.ensure_one()
        if not self.can_create_new_fields:
            raise UserError(_('You do not have permission to create new fields.'))
        self._create_fields()
    
    def action_generate_view(self):
        self.ensure_one()
        if not self.target_model_id:
            raise UserError(_('Please create or select a target model first.'))
        self._maybe_generate_view()
    
    def action_setup_trigger(self):
        self.ensure_one()
        if not self.target_model_id:
            raise UserError(_('Please create or select a target model first.'))
        if not self.server_action_id:
            raise UserError(_('Please select or create a server action first.'))
        self._setup_trigger()

    def action_open_server_action(self):
        self.ensure_one()
        if not self.server_action_id:
            raise UserError(_('No server action is linked yet.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.server',
            'res_id': self.server_action_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_generated_view(self):
        self.ensure_one()
        if not self.generated_view_id:
            raise UserError(_('No generated view exists yet.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'res_id': self.generated_view_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _ensure_target_model(self):
        self.ensure_one()
        if self.target_model_id:
            return

        technical_name = self.new_model_technical_name or self.name
        technical_name = re.sub(r'[^0-9a-zA-Z_]', '_', technical_name).strip('_')
        if not technical_name:
            raise UserError(_('Please provide a valid technical name for the new model.'))
        if not technical_name.startswith('x_'):
            technical_name = 'x_' + technical_name

        existing_model = self.env['ir.model'].search([('model', '=', technical_name)], limit=1)
        if existing_model:
            self.target_model_id = existing_model
            self.target_model_is_new = False
            return

        model = self.env['ir.model'].sudo().create({
            'name': self.new_model_name or self.name,
            'model': technical_name,
            'transient': True,
            'state': 'manual',
        })
        self.target_model_id = model.id
        self.target_model_is_new = True
        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr)

    def _create_fields(self):
        self.ensure_one()
        if not self.target_model_id:
            return

        Fields = self.env['ir.model.fields'].sudo()
        for line in self.field_ids:
            technical_name = self._normalize_field_name(line.field_technical_name)
            existing = Fields.search([
                ('model_id', '=', self.target_model_id.id),
                ('name', '=', technical_name),
            ], limit=1)
            if existing:
                continue

            vals = {
                'model_id': self.target_model_id.id,
                'name': technical_name,
                'field_description': line.field_label,
                'ttype': line.field_type,
                'required': line.required,
                'state': 'manual',
            }
            if line.field_type == 'many2one':
                if not line.relation_model_id:
                    raise UserError(_(
                        "Field '%s' of type Many2one must reference a relation model."
                    ) % line.field_label)
                vals['relation'] = line.relation_model_id.model
            if line.field_type == 'selection':
                vals['selection'] = line.selection_value_text or '[]'

            field = Fields.create(vals)
            line.field_id = field.id

        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr)

    def _maybe_generate_view(self):
        self.ensure_one()
        if not self.target_model_is_new:
            return
        if self.generated_view_id:
            return

        model_name = self.target_model_id.model
        existing_view = self.env['ir.ui.view'].sudo().search([
            ('model', '=', model_name),
            ('type', '=', 'form'),
        ], limit=1)
        if existing_view:
            return

        field_tags = ''.join(
            '<field name="%s"/>' % self._normalize_field_name(field.field_technical_name)
            for field in self.field_ids
        )
        arch = '<form string="%s"><sheet><group>%s</group></sheet></form>' % (self.name, field_tags)
        view = self.env['ir.ui.view'].sudo().create({
            'name': '%s.form.auto' % model_name,
            'model': model_name,
            'type': 'form',
            'arch': arch,
        })
        self.generated_view_id = view.id

    def _setup_trigger(self):
        self.ensure_one()
        if self.trigger_type == 'menu':
            if self.menu_id:
                return
            menu = self.env['ir.ui.menu'].sudo().create({
                'name': self.name,
                'parent_id': False,
                'action': 'ir.actions.server,%d' % self.server_action_id.id,
            })
            self.menu_id = menu.id
        elif self.trigger_type == 'contextual':
            self.server_action_id.sudo().write({
                'binding_model_id': self.target_model_id.id,
                'binding_type': 'action',
                'binding_view_types': 'list',
            })

    def _normalize_field_name(self, value):
        technical_name = re.sub(r'[^0-9a-zA-Z_]', '_', value or '').strip('_')
        if not technical_name:
            raise UserError(_('Each field requires a valid technical name.'))
        if not technical_name.startswith('x_'):
            technical_name = 'x_' + technical_name
        return technical_name

    def unlink(self):
        for record in self:
            if record.state == 'confirmed':
                raise UserError(_('Cannot delete a confirmed report definition.'))
        return super().unlink()
