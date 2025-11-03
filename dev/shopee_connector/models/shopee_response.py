from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class ShopeeResponse(models.Model):
    _name = 'shopee.response'
    _description = 'Shopee Response'
    _order = 'create_date desc'

    # General invoice information
    name = fields.Char(string='Name', related='shopee_connector_id.name')
    shopee_connector_id = fields.Many2one('shopee.connector', string='Shopee Connector')
    type = fields.Selection([
        ('get', 'GET'),
        ('post', 'POST'),
        ('put', 'PUT'),
        ('delete', 'DELETE'),
    ], string='Type')

    response_json = fields.Text(string='Response JSON')
