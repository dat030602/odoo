# -*- coding: utf-8 -*-

from odoo import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        return super(SaleOrder, self.with_context(custom_sale_order_create_mrp=self))._action_confirm()

    def _update_mrp_production(self, dict_value={}):
        self.ensure_one()
        mrp_production = self.env["mrp.production"].search([
            ("sale_order_id", "=", self.id),
            ("state", "in", ["draft", "confirmed"])
        ])
        if mrp_production and dict_value:
            mrp_production.update(dict_value)

    def write(self, values):
        res = super(SaleOrder, self).write(values)
        if "name" in values:
            self._update_mrp_production({"name": self.name})
        if "partner_id" in values:
            self._update_mrp_production({"partner_id": self.partner_id.id})
        return res

    def action_preview_production(self):
        return {
            'name': "production",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'mrp.production',
            'domain': [('sale_order_id','=', self.id)]
        }

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _check_run_mrp(self, product_uom_qty=0):
        self.ensure_one()
        if not self:
            return False, False, 0
        has_mrp_production = self.env["mrp.production"].search([
            ("sale_order_id", "=", self.order_id.id),
            ("product_id", "=", self.product_id.id),
            ("state", "in", ["draft", "confirmed"])
        ])
        mrp_has_draft = has_mrp_production.filtered(lambda x: x.state == "draft")
        mrp_has_confirmed = has_mrp_production.filtered(lambda x: x.state == "confirmed")
        if has_mrp_production:
            if mrp_has_draft and mrp_has_confirmed:
                if self.product_uom_qty > product_uom_qty:
                    # Minus qty
                    return True, False, product_uom_qty - sum(mrp_has_confirmed.mapped("product_qty"))
                elif self.product_uom_qty < product_uom_qty:
                    # Plus qty
                    return True, True, product_uom_qty - self.product_uom_qty
            else:
                if self.product_uom_qty > product_uom_qty:
                    # Minus qty
                    return True, False, product_uom_qty
                elif self.product_uom_qty < product_uom_qty:
                    # Plus qty
                    return True, True, product_uom_qty - self.product_uom_qty
        else:
            return False, False, 0

    @api.model_create_multi
    def create(self, vals_list):
        list_not_duplicate = []
        if vals_list:
            [list_not_duplicate.append(val.get("order_id")) for val in vals_list if val.get("order_id") not in list_not_duplicate]
        if len(list_not_duplicate) == 1:
            return super(SaleOrderLine, self.with_context(custom_sale_order_line_create_mrp=True, custom_sale_order_line_create_data_mrp=vals_list, custom_sale_order_create_mrp=self.order_id.browse(list_not_duplicate[0]))).create(vals_list)
        return super(SaleOrderLine, self).create(vals_list)

    def write(self, values):
        lines = self.env['sale.order.line']
        if 'product_uom_qty' in values:
            lines = self.filtered(lambda r: r.state == 'sale' and not r.is_expense)
        if lines:
            mrp, increase_qty, qty = self._check_run_mrp(values.get("product_uom_qty"))
            if not mrp:
                return super(SaleOrderLine, self.with_context(custom_sale_order_create_mrp=self.order_id)).write(values)
            else:
                dict_value = {
                    "sale_order": self.order_id,
                    "sale_order_line": self,
                    "is_increase_qty": increase_qty,
                    "qty_not_update": self.product_uom_qty,
                    "qty_update": qty
                }
                return super(SaleOrderLine, self.with_context(custom_sale_order_line_qty_mrp=dict_value, custom_sale_order_create_mrp=self.order_id)).write(values)
        return super(SaleOrderLine, self).write(values)
