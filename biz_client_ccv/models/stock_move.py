# -*- coding: utf-8 -*-


from odoo import models, api, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = "stock.move"

    def _trigger_scheduler(self):
        if self._context.get("custom_sale_order_line_qty_mrp"):
            dict_value = self._context.get("custom_sale_order_line_qty_mrp")
            sale_order_id = dict_value["sale_order"]
            sale_order_line_id = dict_value["sale_order_line"]
            mrp_production_ids = self.env["mrp.production"].search([
                ("sale_order_id", "=", sale_order_id.id),
                ("product_id", "=", sale_order_line_id.product_id.id),
                ("state", "in", ["draft", "confirmed"])
            ])
            mrp_has_draft = mrp_production_ids.filtered(lambda x: x.state == "draft").sorted(reverse=True)
            mrp_has_confirmed = mrp_production_ids.filtered(lambda x: x.state == "confirmed").sorted(reverse=True)

            confirm_qty = 0
            for mc in mrp_has_confirmed:
                product_uom_qty = sum(
                    sale_order_id.order_line.filtered(lambda x: x.product_id.id == mc.product_id.id).mapped(
                        "product_uom_qty"))
                message = _("""
                    Order %s changed the order quantity %s
                """) % (sale_order_id.name, product_uom_qty)
                mc.sudo().message_post(
                    author_id=self.env.user.partner_id.id,
                    body=message
                )
                confirm_qty += mc.product_qty

            mrp_sum_qty = sum(mrp_production_ids.mapped('product_qty'))

            if mrp_has_draft:
                mrp_user = mrp_has_draft.filtered(lambda x: x.user_id)
                mrp_user_qty = sum(mrp_user.mapped('product_qty')) + confirm_qty

                for mrp_draft in mrp_has_draft:
                    product_uom_qty = sum(
                        sale_order_id.order_line.filtered(lambda x: x.product_id.id == mrp_draft.product_id.id).mapped(
                            "product_uom_qty"))
                    if dict_value["is_increase_qty"] is False:
                        if mrp_draft.user_id:
                            mrp_draft.mrp_note_increase(sale_order_id.name, product_uom_qty)
                            return

                        elif product_uom_qty < mrp_sum_qty:
                            mrp_draft.mrp_note_increase(sale_order_id.name, product_uom_qty)

                            mrp_user.mrp_note_increase(sale_order_id.name, product_uom_qty)
                            if product_uom_qty > mrp_user_qty:
                                mrp_draft.update({"product_qty": product_uom_qty - mrp_user_qty})
                            message = _("The selling quantity is smaller than the total production quantity of the orders.")
                            sale_order_id.message_post(body=message)
                            return

                        elif product_uom_qty > mrp_sum_qty:
                            mrp_draft.update({"product_qty": product_uom_qty - mrp_sum_qty})
                            return

                    else:
                        if not mrp_draft.user_id:
                            mrp_draft.update({"product_qty": product_uom_qty - mrp_user_qty})
                            return

                        else:
                            mrp_draft.mrp_note_increase(sale_order_id.name, product_uom_qty)

            if mrp_has_confirmed and not mrp_has_draft:
                for mrp_confirmed in mrp_has_confirmed:
                    if dict_value["is_increase_qty"] is True:
                        break
                    elif dict_value["is_increase_qty"] is False:
                        product_uom_qty = sum(sale_order_id.order_line.filtered(
                            lambda x: x.product_id.id == mrp_draft.product_id.id).mapped("product_uom_qty"))

                        mrp_confirmed.mrp_note_increase(sale_order_id.name, product_uom_qty)
                        return

        elif self._context.get("custom_sale_order_line_create_mrp"):
            sale_order_id = self._context.get("custom_sale_order_create_mrp")
            list_value = self._context.get("custom_sale_order_line_create_data_mrp")
            for line in list_value:
                product_id = self.env["product.product"].browse(int(line.get("product_id")))
                mrp_production_ids = self.env["mrp.production"].search([
                    ("sale_order_id", "=", sale_order_id.id),
                    ("product_id", "=", product_id.id),
                    ("user_id", "=", False),
                    ("state", "in", ["draft"])
                ])

                mrp_has_draft = mrp_production_ids.filtered(lambda x: x.state == "draft").sorted(reverse=True)
                mrp_has_confirmed = mrp_production_ids.filtered(lambda x: x.state == "confirmed").sorted(reverse=True)

                confirm_qty = 0
                for mc in mrp_has_confirmed:
                    confirm_qty += mc.product_qty

                if mrp_has_draft:
                    mrp_user = mrp_has_draft.filtered(lambda x: x.user_id)
                    mrp_user_qty = sum(mrp_user.mapped('product_qty')) + confirm_qty
                    for mrp_draft in mrp_has_draft:
                        product_qty = mrp_draft.product_qty + line.get("product_uom_qty")
                        mrp_draft.update({"product_qty": product_qty - mrp_user_qty})
                        return

        return super(StockMove, self)._trigger_scheduler()

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        if self._context.get("custom_sale_order_create_mrp") and self._context.get("from_orderpoint"):
            res['sale_order_id'] = self._context.get("custom_sale_order_create_mrp").id
            res['sale_order_partner_id'] = self._context.get("custom_sale_order_create_mrp").partner_id.id
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(move.state not in ('draft', 'cancel', 'confirmed') for move in self):
            raise UserError(_('You can only delete draft, confirmed or cancelled moves.'))