from odoo import api, fields, models
from ..core.schema_builder import invalidate_schema_cache


class DnGraphqlModel(models.Model):
    _name = 'dn.graphql.model'
    _description = 'GraphQL Model Whitelist Definition'
    _order = 'model_name asc'

    model_id = fields.Many2one(
        'ir.model',
        string='Odoo Model',
        required=True,
        ondelete='cascade',
        index=True
    )
    model_name = fields.Char(
        string='Technical Model Name',
        related='model_id.model',
        store=True,
        index=True
    )
    name = fields.Char(
        string='Display Title',
        compute='_compute_name',
        store=True
    )
    active = fields.Boolean(
        string='Active in Schema',
        default=True,
        index=True
    )

    allow_read = fields.Boolean(
        string='Allow Query',
        default=True,
        help="Enable GraphQL Connection query for this model."
    )
    allow_create = fields.Boolean(
        string='Allow Create Mutation',
        default=True,
        help="Enable `<model>__create` GraphQL mutation."
    )
    allow_write = fields.Boolean(
        string='Allow Update Mutation',
        default=True,
        help="Enable `<model>__update` GraphQL mutation."
    )
    allow_unlink = fields.Boolean(
        string='Allow Delete Mutation',
        default=True,
        help="Enable `<model>__delete` GraphQL mutation."
    )

    field_ids = fields.Many2many(
        'ir.model.fields',
        'dn_graphql_model_fields_rel',
        'model_setting_id',
        'field_id',
        string='Exposed Fields',
        domain="[('model_id', '=', model_id)]",
        help="Specify allowed fields to expose. If left empty, all safe non-binary fields are exposed."
    )

    default_limit = fields.Integer(
        string='Default Page Limit',
        default=20,
        help="Default number of records returned if `first` argument is omitted."
    )
    max_limit = fields.Integer(
        string='Maximum Page Limit',
        default=100,
        help="Maximum records allowed per request to protect against large data scraping."
    )

    _sql_constraints = [
        ('unique_model', 'unique(model_id)', 'This Odoo model is already configured in the GraphQL Gateway!')
    ]

    @api.depends('model_id', 'model_name')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.model_id.name or rec.model_name or 'Undefined'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        invalidate_schema_cache(self.env.cr.dbname)
        return records

    def write(self, vals):
        res = super().write(vals)
        invalidate_schema_cache(self.env.cr.dbname)
        return res

    def unlink(self):
        res = super().unlink()
        invalidate_schema_cache(self.env.cr.dbname)
        return res

    @api.model
    def seed_default_installed_models(self):
        """Auto-whitelists common core ERP models if installed in the current database."""
        candidates = [
            'res.partner',
            'sale.order',
            'purchase.order',
            'stock.picking',
            'account.move',
            'mrp.production',
        ]
        for mname in candidates:
            if mname in self.env:
                existing = self.search([('model_name', '=', mname)], limit=1)
                if not existing:
                    model_rec = self.env['ir.model'].search([('model', '=', mname)], limit=1)
                    if model_rec:
                        self.create({
                            'model_id': model_rec.id,
                            'allow_read': True,
                            'allow_create': True,
                            'allow_write': True,
                            'allow_unlink': True,
                            'default_limit': 20,
                            'max_limit': 100,
                            'active': True,
                        })
