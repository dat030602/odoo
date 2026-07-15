# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    stock_warehouse_ids = fields.Many2many(comodel_name="stock.warehouse", relation="stock_warehouse_user_rel",
                                           column1="user_id", column2="stock_warehouse_id", copy=False)

