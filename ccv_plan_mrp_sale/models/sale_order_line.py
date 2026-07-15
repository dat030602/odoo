from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    is_delivered = fields.Boolean('Đã giao hàng', compute="_compute_is_delivered", store=True)

    @api.depends('product_uom_qty','qty_delivered')
    def _compute_is_delivered(self):
        for rec in self:
            rec.is_delivered = rec.product_uom_qty <= rec.qty_delivered

    def get_clean_name(self):
        self.ensure_one()
        if self.name and ']' in self.name:
            return self.name.split(']', 1)[1].strip()
        return self.name
