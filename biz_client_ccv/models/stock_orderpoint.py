# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from dateutil import relativedelta
from psycopg2 import OperationalError

from odoo import SUPERUSER_ID, models, registry, fields
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import float_compare, split_every

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    def _check_has_mrp(self, order_line=False):
        if not order_line:
            return False
        for line in order_line:
            has_mrp_production = self.env["mrp.production"].search([
                ("sale_order_id", "=", line.order_id.id),
                ("product_id", "=", line.product_id.id),
                ("state", "in", ["draft", "confirmed"]),
                ("user_id", "=", False)
            ])
            if has_mrp_production:
                return True
            return False
    def _prepare_procurement_values(self, date=False, group=False):
        values = super()._prepare_procurement_values(date=date, group=group)
        if self._context.get("custom_sale_order_create_mrp"):
            values['sale_order_id'] = self._context.get("custom_sale_order_create_mrp").id
            values['sale_order_partner_id'] = self._context.get("custom_sale_order_create_mrp").partner_id.id
        return values

    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=None, raise_user_error=True):
        if self._context.get("custom_sale_order_create_mrp"):
            self = self.with_company(company_id)

            for orderpoints_batch_ids in split_every(1000, self.ids):
                if use_new_cursor:
                    cr = registry(self._cr.dbname).cursor()
                    self = self.with_env(self.env(cr=cr))
                try:
                    orderpoints_batch = self.env['stock.warehouse.orderpoint'].browse(orderpoints_batch_ids)
                    all_orderpoints_exceptions = []
                    while orderpoints_batch:
                        procurements = []
                        for orderpoint in orderpoints_batch:
                            sale_order = self._context.get("custom_sale_order_create_mrp")
                            sale_order_line = sale_order.order_line.filtered(
                                lambda x: x.product_id == orderpoint.product_id)
                            sum_product_uom_qty = sum(sale_order_line.mapped("product_uom_qty"))

                            if self._context.get("custom_sale_order_line_create_mrp"):
                                # Create
                                has_mrp = self._check_has_mrp(sale_order_line)
                                if has_mrp:
                                    continue
                                if len(sale_order_line) > 1:
                                    # Case duplicate product_id
                                    mrp = self.env["mrp.production"].search([
                                        ("sale_order_id", "=", sale_order.id),
                                        ("product_id", "=", sale_order_line[0].product_id.id),
                                        ("state", "in", ["draft", "confirmed"]),
                                        ("user_id", "!=", False)
                                    ])
                                    if mrp:
                                        sum_product_uom_qty -= sum(mrp.mapped("product_qty"))
                            elif self._context.get("custom_sale_order_line_qty_mrp") and sale_order_line:
                                # write
                                dict_value = self._context.get("custom_sale_order_line_qty_mrp")
                                if orderpoint.product_id.id != dict_value["sale_order_line"]["product_id"].id:
                                    continue
                                sum_product_uom_qty = dict_value["qty_update"]

                            if float_compare(sum_product_uom_qty, 0.0,
                                             precision_rounding=orderpoint.product_uom.rounding) == 1:
                                date = orderpoint._get_orderpoint_procurement_date()
                                global_visibility_days = self.env['ir.config_parameter'].sudo().get_param(
                                    'stock.visibility_days')
                                if global_visibility_days:
                                    date -= relativedelta.relativedelta(days=int(global_visibility_days))
                                values = orderpoint._prepare_procurement_values(date=date)

                                procurements.append(self.env['procurement.group'].Procurement(
                                    orderpoint.product_id, sum_product_uom_qty, orderpoint.product_uom,
                                    orderpoint.location_id, orderpoint.name, sale_order.name,
                                    orderpoint.company_id, values))

                        try:
                            with self.env.cr.savepoint():
                                self.env['procurement.group'].with_context(from_orderpoint=True).run(procurements, raise_user_error=raise_user_error)
                        except ProcurementException as errors:
                            orderpoints_exceptions = []
                            for procurement, error_msg in errors.procurement_exceptions:
                                orderpoints_exceptions += [(procurement.values.get('orderpoint_id'), error_msg)]
                            all_orderpoints_exceptions += orderpoints_exceptions
                            failed_orderpoints = self.env['stock.warehouse.orderpoint'].concat(*[o[0] for o in orderpoints_exceptions])
                            if not failed_orderpoints:
                                _logger.error('Unable to process orderpoints')
                                break
                            orderpoints_batch -= failed_orderpoints

                        except OperationalError:
                            if use_new_cursor:
                                cr.rollback()
                                continue
                            else:
                                raise
                        else:
                            orderpoints_batch._post_process_scheduler()
                            break

                    # Log an activity on product template for failed orderpoints.
                    for orderpoint, error_msg in all_orderpoints_exceptions:
                        existing_activity = self.env['mail.activity'].search([
                            ('res_id', '=', orderpoint.product_id.product_tmpl_id.id),
                            ('res_model_id', '=', self.env.ref('product.model_product_template').id),
                            ('note', '=', error_msg)])
                        if not existing_activity:
                            orderpoint.product_id.product_tmpl_id.sudo().activity_schedule(
                                'mail.mail_activity_data_warning',
                                note=error_msg,
                                user_id=orderpoint.product_id.responsible_id.id or SUPERUSER_ID,
                            )

                finally:
                    if use_new_cursor:
                        try:
                            cr.commit()
                        finally:
                            cr.close()
                        _logger.info("A batch of %d orderpoints is processed and committed", len(orderpoints_batch_ids))

            return {}
        else:
            return super(StockWarehouseOrderpoint, self)._procure_orderpoint_confirm(use_new_cursor=use_new_cursor, company_id=company_id, raise_user_error=raise_user_error)