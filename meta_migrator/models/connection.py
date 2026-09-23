from odoo import fields, models, _
from odoo.exceptions import UserError

from .rpc_helper import OdooRPC, OdooRPCError


class MetaMigrationConnection(models.Model):
    _name = 'meta.migration.connection'
    _description = 'Odoo Connection (Meta Migrator)'
    _order = 'name'

    name = fields.Char(required=True)
    url = fields.Char(string='URL', required=True, help="e.g. https://mycompany.odoo.com")
    db = fields.Char(string='Database', required=True)
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    active = fields.Boolean(default=True)
    note = fields.Char(string='Note')

    def _get_rpc(self):
        self.ensure_one()
        return OdooRPC(self.url, self.db, self.username, self.password)

    def action_test_connection(self):
        self.ensure_one()
        rpc = self._get_rpc()
        try:
            uid = rpc.authenticate()
        except OdooRPCError as e:
            raise UserError(str(e))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection Successful'),
                'message': _('Logged in to %s (uid=%s)') % (self.url, uid),
                'type': 'success',
                'sticky': False,
            },
        }
