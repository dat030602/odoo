from odoo import models, fields


class DnGraphqlKeyShow(models.TransientModel):
    _name = 'dn.graphql.key.show'
    _description = 'Show GraphQL API Key'

    key = fields.Char(string="API Key Token", readonly=True)
