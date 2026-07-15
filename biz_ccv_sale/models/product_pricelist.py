# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
import sys
sys.setrecursionlimit(10000)
from odoo.exceptions import ValidationError


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    
    def unlink(self):
        # for record in self:
        self._cr.execute('''
            DELETE FROM product_pricelist_item
            WHERE pricelist_id in %s
        ''', [tuple(self.ids)])
                
        return super(ProductPricelist, self).unlink()