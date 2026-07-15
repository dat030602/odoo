# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.returns('self')
    def _filter_visible_menus(self):
        menu_ids = super(IrUiMenu, self)._filter_visible_menus()
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            first_menu_remove = self.env.ref('biz_ccv_sale.coordinate_checkin_history_menu_crm')
            second_menu_remove = self.env.ref('biz_ccv_sale.sale_route_menu_crm')
            thirt_menu_remove = self.env.ref('biz_ccv_sale.sale_route_report_menu_report_crm')

            if first_menu_remove:
                menu_ids = menu_ids - first_menu_remove
            if second_menu_remove:
                menu_ids = menu_ids - second_menu_remove
            if thirt_menu_remove:
                menu_ids = menu_ids - thirt_menu_remove
            
        return menu_ids
