from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class sale_order_line(models.Model):
    _inherit = 'sale.order'

    def _get_vals_create_pk(self,time=0):
        res = super(sale_order_line,self)._get_vals_create_pk(time)
        context = self.env.context
        plan_sale_id = context.get("plan_sale_id", False)
        if plan_sale_id:
            res.update({'plan_sale_id': plan_sale_id})
        return res
