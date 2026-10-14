from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dn_graphql_max_depth = fields.Integer(
        string='Maximum Query Depth',
        default=6,
        config_parameter='dn_graphql_gateway.max_depth',
        help="Maximum allowable nested selection levels in GraphQL queries."
    )
    dn_graphql_rate_limit_minute = fields.Integer(
        string='Rate Limit (Requests / Minute / Key)',
        default=60,
        config_parameter='dn_graphql_gateway.rate_limit_minute',
        help="Maximum requests permitted per API key in a 1-minute window."
    )
    dn_graphql_max_nodes = fields.Integer(
        string='Max Records per Query',
        default=1000,
        config_parameter='dn_graphql_gateway.max_nodes',
        help="Upper boundary of nodes retrieved across nested relationships."
    )
