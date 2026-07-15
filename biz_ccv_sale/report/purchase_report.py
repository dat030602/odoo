# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    purchase_order_type_id = fields.Many2one(comodel_name='purchase.order.type', string="Purchase Order Type ID")

    def _select(self):
        return super(PurchaseReport, self)._select() + ", pot.id as purchase_order_type_id"

    def _from(self):
        return super(PurchaseReport, self)._from() + " left join purchase_order_type pot on (pot.id=po.purchase_order_type_id)"

    def _group_by(self):
        return super(PurchaseReport, self)._group_by() + ", pot.id"