from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class stock_picking_type(models.Model):
    _inherit = 'stock.picking'

    plan_sale_id = fields.Many2one('ccv.sale.plan.export')


