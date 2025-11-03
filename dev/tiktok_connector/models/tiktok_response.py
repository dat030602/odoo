from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class TikTokResponse(models.Model):
    _name = 'tiktok.response'
    _description = 'TikTok Response'
    _order = 'create_date desc'

    # General invoice information
    name = fields.Char(string='Name', related='tiktok_connector_id.name')
    tiktok_connector_id = fields.Many2one('tiktok.connector', string='TikTok Connector')
    type = fields.Selection([
        ('get', 'GET'),
        ('post', 'POST'),
        ('put', 'PUT'),
        ('delete', 'DELETE'),
    ], string='Type')

    response_json = fields.Text(string='Response JSON')
