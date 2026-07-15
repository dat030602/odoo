# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.osv import expression


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get("is_happy_birthday_template") and self._context.get("is_happy_birthday_template") == "happy_birthday":
            args = expression.AND([[("model", "in", ["res.partner", "hr.employee"])], args])
        elif self._context.get("is_happy_birthday_template") and self._context.get("is_happy_birthday_template") in ["order_confirmation"]:
            args = expression.AND([[("model", "in", ["sale.order"])], args])
        elif self._context.get("is_happy_birthday_template") and self._context.get("is_happy_birthday_template") in ["order_completion"]:
            args = expression.AND([[("model", "in", ["stock.picking"])], args])
        return super(IrModel, self)._name_search(name, args, operator, limit, name_get_uid)
