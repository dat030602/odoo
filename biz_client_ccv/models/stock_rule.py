# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import datetime


from odoo import models

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        mo_values = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
        if self._context.get("custom_sale_order_create_mrp") and self._context.get("from_orderpoint"):
            mo_values['sale_order_id'] = values.get("sale_order_id")
            mo_values['sale_order_partner_id'] = values.get("sale_order_partner_id")
            mo_values['date_planned_start'] = datetime.datetime.now()
            mo_values['date_deadline'] = datetime.datetime.now()
        return mo_values
