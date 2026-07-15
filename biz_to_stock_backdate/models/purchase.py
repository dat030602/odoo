from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    stock_date_receipt = fields.Datetime('Inventory date(used for warehouse receipts)')
    date_approve = fields.Datetime('Confirmation Date', readonly=0, index=True, copy=False)

    def button_confirm(self):
        for order in self:
            date_order = order.date_order
            res = super(PurchaseOrder, order).button_confirm()
            if order.picking_ids:
                for picking in order.picking_ids:
                    picking.stock_date_receipt = order.stock_date_receipt
            order.date_approve = date_order
            return res

    def button_confirm_multi(self):
        for rec in self:
            if rec.state in ['draft', 'sent']:
                rec.button_confirm()
