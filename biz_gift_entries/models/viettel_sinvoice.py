# -*- coding: utf-8 -*-
from datetime import datetime
import time
from odoo import models, fields, api,_
import json
from odoo.exceptions import UserError,ValidationError

class ViettelSinvoice(models.Model):
    _inherit = "viettel.sinvoice"

    def create_data_sinvoice_line_gift_entries(self, line):
        self.ensure_one()
        results = []
        name = line.name or line.product_id.name
        price_unit = line.product_id.lst_price
        vals = {
                'name': name,
                'origin': name,
                'account_id': line.account_id.id,
                'price_unit': price_unit,
                'quantity': line.quantity,
                'discount': 0,
                'product_uom_id': line.product_uom_id.id,
                'product_id': line.product_id.id or False,
                'tax_ids': [(6, 0, line.move_id.stock_move_id.sale_line_id.tax_id.ids)],
                'sinvoice_id': self.id,
            }
        results.append(vals)
        return results