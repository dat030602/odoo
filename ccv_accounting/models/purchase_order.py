from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_is_zero
from odoo import SUPERUSER_ID
from datetime import datetime, timedelta
import logging
import pytz
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.invoice_lines.move_id','order_line.move_ids.account_move_ids','invoice_ids.move_tax_import_id')
    def _compute_invoice(self):
        res = super(PurchaseOrder,self)._compute_invoice()
        for order in self:
            order.invoice_ids |= order.invoice_ids.mapped('move_tax_import_id')
            order.invoice_count = len(order.invoice_ids)
        return res
