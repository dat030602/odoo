import logging
import odoo
from odoo import fields, models

_logger = logging.getLogger(__name__)


class DnGraphqlLog(models.Model):
    _name = 'dn.graphql.log'
    _description = 'GraphQL Request Audit Log'
    _order = 'create_date desc, id desc'

    request_id = fields.Char(string='Request UUID', index=True, readonly=True)
    key_rec_id = fields.Many2one('dn.graphql.key', string='API Key Record', index=True, readonly=True)
    api_key_name = fields.Char(string='API Key Identifier', index=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Executed User', index=True, readonly=True)
    ip_address = fields.Char(string='Client IP Address', readonly=True)
    operation_name = fields.Char(string='Operation Name', readonly=True)
    query_text = fields.Text(string='GraphQL Query (Masked)', readonly=True)
    variables_text = fields.Text(string='Variables (Masked)', readonly=True)
    request_body = fields.Text(string='Request Body', readonly=True)
    response_body = fields.Text(string='Response Body', readonly=True)
    status_code = fields.Integer(string='HTTP Status Code', readonly=True)
    duration_ms = fields.Float(string='Duration (ms)', readonly=True)
    error_code = fields.Char(string='Error Code', readonly=True)
    error_message = fields.Text(string='Error Details', readonly=True)
    node_count = fields.Integer(string='Records Retrieved / Modified', readonly=True)
    rolled_back = fields.Boolean(string='Atomic Rollback Executed', readonly=True)

    @classmethod
    def log_request_isolated(cls, env, log_vals: dict):
        """
        Writes log record using an independent database cursor in production.
        In test runner context (where registry cursor is restricted), writes directly via env.
        Wrapped in savepoint to prevent aborting active transactions.
        """
        if not env:
            return

        is_test = odoo.tools.config.get('test_enable') or hasattr(env.cr, '_readonly')

        if not is_test:
            try:
                from odoo.modules.registry import Registry
                registry = Registry(env.cr.dbname)
                with registry.cursor() as log_cr:
                    isolated_env = odoo.api.Environment(log_cr, odoo.SUPERUSER_ID, {})
                    isolated_env['dn.graphql.log'].create(log_vals)
                    log_cr.commit()
                return
            except Exception as e:
                _logger.debug("Isolated cursor failed, falling back to env: %s", e)

        try:
            with env.cr.savepoint():
                env['dn.graphql.log'].sudo().create(log_vals)
        except Exception as e:
            _logger.debug("Failed to commit GraphQL log (read-only transaction): %s", e)
