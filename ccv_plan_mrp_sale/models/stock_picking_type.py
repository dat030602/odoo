from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class stock_picking_type(models.Model):
    _inherit = 'stock.picking.type'

    factory_name = fields.Char('Tên nhà máy')
