from odoo import api, fields, models
from ..core.schema_builder import invalidate_schema_cache


class DnGraphqlDeny(models.Model):
    _name = 'dn.graphql.deny'
    _description = 'GraphQL Blocklist / Deny Policy'
    _order = 'key_rec_id asc, api_key_id asc, model_name asc'

    name = fields.Char(
        string='Rule Summary',
        compute='_compute_name',
        store=True
    )
    key_rec_id = fields.Many2one(
        'dn.graphql.key',
        string='Target API Key',
        ondelete='cascade',
        index=True,
        help="Specific API Key to restrict. Leave empty to enforce this rule globally across all clients."
    )
    api_key_id = fields.Many2one(
        'res.users.apikeys',
        string='Native API Key',
        ondelete='set null',
        index=True,
        help="Optional fallback to native Odoo API Key."
    )
    is_global = fields.Boolean(
        string='Is Global Policy',
        compute='_compute_is_global',
        store=True,
        index=True
    )

    model_id = fields.Many2one(
        'ir.model',
        string='Odoo Model',
        required=True,
        ondelete='cascade',
        index=True
    )
    model_name = fields.Char(
        string='Model Technical Name',
        related='model_id.model',
        store=True,
        index=True
    )

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Restricted Field',
        domain="[('model_id', '=', model_id)]",
        ondelete='cascade',
        help="Leave blank to block the entire model from being queried or modified."
    )
    field_name = fields.Char(
        string='Field Technical Name',
        related='field_id.name',
        store=True,
        index=True
    )

    operation = fields.Selection([
        ('all', 'All Operations (Read & Write)'),
        ('read', 'Read Only (Queries)'),
        ('write', 'Write Only (Updates)'),
        ('create', 'Create Only'),
        ('unlink', 'Delete Only')
    ], string='Restricted Operation', default='all', required=True)

    active = fields.Boolean(
        string='Active',
        default=True,
        index=True
    )
    reason = fields.Char(
        string='Security Justification',
        default="Restricted by enterprise access control policy."
    )

    def init(self):
        super().init()
        # Self-healing: clear any orphan foreign keys pointing to deleted native apikeys
        try:
            self.env.cr.execute("""
                UPDATE dn_graphql_deny
                SET api_key_id = NULL
                WHERE api_key_id IS NOT NULL
                  AND api_key_id NOT IN (SELECT id FROM res_users_apikeys)
            """)
        except Exception:
            pass

    @api.depends('key_rec_id', 'api_key_id')
    def _compute_is_global(self):
        for rec in self:
            rec.is_global = not bool(rec.key_rec_id or rec.api_key_id)

    @api.depends('key_rec_id', 'api_key_id', 'model_name', 'field_name', 'operation')
    def _compute_name(self):
        for rec in self:
            scope_prefix = "[GLOBAL]"
            if rec.key_rec_id:
                scope_prefix = f"[Key: {rec.key_rec_id.name}]"
            elif rec.api_key_id:
                try:
                    if rec.api_key_id.exists():
                        scope_prefix = f"[Key: {rec.api_key_id.display_name or rec.api_key_id.name}]"
                except Exception:
                    pass
            target = f"{rec.model_name}.{rec.field_name}" if rec.field_name else f"{rec.model_name} (ALL)"
            rec.name = f"{scope_prefix} Block {target} [{rec.operation}]"

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
