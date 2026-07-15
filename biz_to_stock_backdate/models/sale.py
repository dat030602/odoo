from odoo import fields, models, api

READONLY_FIELD_STATES = {
    state: [('readonly', True)]
    for state in {'sale', 'done', 'cancel'}
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # def _defaut_date_order(self):
    #     return False

    stock_date_receipt = fields.Datetime('Inventory date(used for warehouse receipts)')


    def action_confirm(self):
        for order in self:
            date_order = order.date_order
            res = super(SaleOrder, order).action_confirm()
            if order.picking_ids:
                for picking in order.picking_ids:
                    picking.stock_date_receipt = order.stock_date_receipt
            # if order.mrp_production_ids:
            #     for mrp in order.mrp_production_ids:
            #         mrp.stock_date_receipt = order.stock_date_receipt
            order.date_order = date_order
            return res

    def action_confirm_multi(self):
        for rec in self:
            if rec.state in ['draft', 'sent']:
                rec.action_confirm()