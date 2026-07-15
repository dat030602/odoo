# -*- coding: utf-8 -*-


from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _change_standard_price(self, new_price):
        return

    @api.model
    def _svl_empty_stock(self, description, product_category=None, product_template=None):
        impacted_products = self.env['product.product']
        products_orig_quantity_svl = {}

        # empty out the stock for the impacted products
        empty_stock_svl_list = []
        return empty_stock_svl_list, products_orig_quantity_svl, impacted_products

    @api.model
    def _svl_empty_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        return move_vals_list


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def _svl_empty_stock(self, description, product_category=None, product_template=None):
        impacted_products = self.env['product.product']
        products_orig_quantity_svl = {}
        # empty out the stock for the impacted products
        empty_stock_svl_list = []
        return empty_stock_svl_list, products_orig_quantity_svl, impacted_products

    @api.model
    def _svl_empty_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        return move_vals_list