# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

from odoo.exceptions import UserError


class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = "mrp.production"

    sale_order_partner_id = fields.Many2one(comodel_name="res.partner", string="Partner", copy=False)
    sale_order_id = fields.Many2one(comodel_name="sale.order", string="Order", copy=False)
    is_hide_mrp_production_childs = fields.Boolean(string="Is hide mrp production childs", compute="_compute_is_hide_mrp_production_childs")

    def _compute_is_hide_mrp_production_childs(self):
        for record in self:
            is_hide_mrp_production_childs = True
            if self.env.user.has_group('mrp.group_mrp_manager'):
                is_hide_mrp_production_childs = False
            elif self.env.user.has_group('biz_client_ccv.group_mrp_manager_production'):
                mrp_production_ids = record._get_children().filtered(lambda x: x.picking_type_id.warehouse_id in self.env.user.stock_warehouse_ids.ids)
                if mrp_production_ids:
                    is_hide_mrp_production_childs = False
            elif self.env.user.has_group('mrp.group_mrp_user'):
                mrp_production_ids = record._get_children().filtered(
                    lambda x: x.picking_type_id.warehouse_id in self.env.user.stock_warehouse_ids.ids and x.user_id == self.env.user)
                if mrp_production_ids:
                    is_hide_mrp_production_childs = False
            record.is_hide_mrp_production_childs = is_hide_mrp_production_childs

    @api.ondelete(at_uninstall=False)
    def _unlink_record_has_group_mrp_user(self):
        if (self.env.user.has_group('mrp.group_mrp_user') or self.env.user.has_group('biz_client_ccv.group_mrp_manager_production')) and not self.env.user.has_group('mrp.group_mrp_manager'):
            raise UserError(_("You do not have permission to delete a work order."))

        if self.sale_order_id:
            raise UserError(_("You cannot delete a work order created from an order."))

    def action_cancel(self):
        if self.sale_order_id:
            raise UserError(_("You cannot cancel a work order created from an order."))

        return super(MrpProduction, self).action_cancel()

    def action_confirm(self):
        if self._context.get("custom_cron_run_scheduler"):
            return True
        elif self._context.get("custom_sale_order_create_mrp"):
            return True
        return super(MrpProduction, self).action_confirm() if self else True

    def mrp_note_increase(self, name,qty):
        for res in self:
            message = _("""
                Order %s changed the order quantity %s
            """) % (name, qty)
            res.sudo().message_post(
                author_id=self.env.user.partner_id.id,
                body=message
            )