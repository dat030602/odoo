import secrets
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class DnGraphqlKey(models.Model):
    _name = 'dn.graphql.key'
    _description = 'GraphQL API Key Management'
    _order = 'id desc'

    name = fields.Char(string="Key Description / Name", required=True, default="GraphQL Client Key")
    user_id = fields.Many2one(
        'res.users',
        string="Assigned User",
        required=True,
        ondelete='cascade',
        help="The service user whose permissions and ACLs govern this API Key."
    )
    company_id = fields.Many2one('res.company', string="Company", related='user_id.company_id', readonly=True)
    expiration_date = fields.Datetime(string="Expiration Date", help="Leave blank for a non-expiring key.")

    key_id = fields.Many2one('res.users.apikeys', string="Native API Key", readonly=True, ondelete='set null')
    key_index = fields.Char(string="Key Prefix / Index", readonly=True, copy=False)
    raw_key = fields.Char(
        string="Secret Key Token",
        readonly=True,
        copy=False,
        help="Displayed upon generation. Copy and store it securely."
    )

    state = fields.Selection([
        ('draft', 'Draft (Not Generated)'),
        ('active', 'Active'),
        ('revoked', 'Revoked'),
    ], default='draft', string="Status", required=True)

    user_group_ids = fields.Many2many(
        'res.groups',
        'dn_graphql_key_res_groups_rel',
        'key_rec_id',
        'group_id',
        string="User Access Groups",
        compute='_compute_user_group_ids',
        inverse='_inverse_user_group_ids',
        help="Manage security groups for the assigned user directly here."
    )

    deny_rule_ids = fields.One2many(
        'dn.graphql.deny',
        'key_rec_id',
        string="Custom Deny Policies",
        help="Blocklist rules specifically assigned to this API Key."
    )
    deny_rule_count = fields.Integer(compute='_compute_deny_rules', string="Deny Rules Count")

    log_ids = fields.One2many(
        'dn.graphql.log',
        compute='_compute_logs',
        string="Request Logs",
        help="Recent requests executed using this key."
    )
    log_count = fields.Integer(compute='_compute_logs', string="Request Count")

    @api.depends('user_id.group_ids')
    def _compute_user_group_ids(self):
        for record in self:
            record.user_group_ids = record.user_id.group_ids if record.user_id else self.env['res.groups']

    def _inverse_user_group_ids(self):
        for record in self:
            if record.user_id:
                record.user_id.group_ids = record.user_group_ids

    @api.depends('deny_rule_ids')
    def _compute_deny_rules(self):
        for record in self:
            record.deny_rule_count = len(record.deny_rule_ids)

    @api.depends('key_index')
    def _compute_logs(self):
        for record in self:
            domain = []
            if record.id and record.key_index:
                domain = ['|', ('key_rec_id', '=', record.id), ('api_key_name', '=like', f"{record.key_index}%")]
            elif record.id:
                domain = [('key_rec_id', '=', record.id)]
            elif record.key_index:
                domain = [('api_key_name', '=like', f"{record.key_index}%")]

            if domain:
                logs = self.env['dn.graphql.log'].search(domain, order='create_date desc, id desc', limit=50)
                record.log_ids = logs
                record.log_count = self.env['dn.graphql.log'].search_count(domain)
            else:
                record.log_ids = self.env['dn.graphql.log']
                record.log_count = 0

    def action_generate_key(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("Please select an Assigned User before generating an API Key."))

        # Ensure user has Internal User access group
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        if group_user and group_user not in self.user_id.group_ids:
            self.user_id.group_ids = [(4, group_user.id)]

        # Generate native API Key using Odoo's native res.users.apikeys
        raw_token = self.env['res.users.apikeys'].with_user(self.user_id).sudo()._generate(
            'graphql',
            self.name,
            self.expiration_date
        )

        index = raw_token[:8]
        self.env.cr.execute("""
            SELECT id FROM res_users_apikeys
            WHERE index = %s AND user_id = %s
            ORDER BY id DESC LIMIT 1
        """, (index, self.user_id.id))
        row = self.env.cr.fetchone()
        key_id = row[0] if row else False

        self.write({
            'raw_key': raw_token,
            'key_id': key_id,
            'key_index': index,
            'state': 'active',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("API Key Generated Successfully"),
                'message': _("Your new API key has been generated and displayed on screen. Please copy and store it securely!"),
                'type': 'success',
                'sticky': True,
            }
        }

    def action_revoke_key(self):
        self.ensure_one()
        if self.key_id and self.key_id.exists():
            self.key_id.sudo()._remove()
        self.write({
            'state': 'revoked',
            'raw_key': False,
            'key_id': False,
        })
        return True

    def action_regenerate_key(self):
        self.ensure_one()
        if self.key_id and self.key_id.exists():
            self.key_id.sudo()._remove()
        return self.action_generate_key()
