# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Sitaram Solutions (<https://sitaramsolutions.in/>).
#
#    For Module Support : info@sitaramsolutions.in  or Skype : contact.hiren1188
#
##############################################################################

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate', digits=(12, 12))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)
    is_invisible = fields.Boolean(compute='_check_is_invisible')
    inverse_manural_currency_exchange_rate = fields.Float(string='Inverse Manual Currency Exchange Rate', digits=(12, 2))

    @api.depends('apply_manual_currency_exchange', 'active_manual_currency_rate')
    def _check_is_invisible(self):
        is_debug = self.user_has_groups('base.group_no_one')
        is_inverse = self.company_id.currency_id.is_inverse
        
        if is_inverse:
            if is_debug:
                self.is_invisible = False
            else:
                self.is_invisible = True
        else:
            self.is_invisible = False
    
    @api.onchange('inverse_manural_currency_exchange_rate')
    def onchange_inverse_manural_currency_exchange_rate(self):
        self.manual_currency_exchange_rate = (1 / self.inverse_manural_currency_exchange_rate) if self.inverse_manural_currency_exchange_rate > 0 else 0

    @api.onchange('company_id','currency_id')
    def onchange_currency_id(self):
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res.update({
            'apply_manual_currency_exchange':self.apply_manual_currency_exchange,
            'manual_currency_exchange_rate':self.manual_currency_exchange_rate,
            'inverse_manural_currency_exchange_rate':self.inverse_manural_currency_exchange_rate,
            'active_manual_currency_rate':self.active_manual_currency_rate,
            })
        return res
    
    # def write(self, vals):
    #     res = super(PurchaseOrder, self).write(vals)
    #     if any(key in vals for key in ['apply_manual_currency_exchange', 'manual_currency_exchange_rate']) and self.invoice_ids:
    #         invoices = self.invoice_ids.filtered(lambda s: s.state != 'posted')
    #         if invoices:
    #             invoices.write({
    #                 'apply_manual_currency_exchange': self.apply_manual_currency_exchange,
    #                 'inverse_manural_currency_exchange_rate': self.inverse_manural_currency_exchange_rate,
    #                 'manual_currency_exchange_rate': self.manual_currency_exchange_rate,
    #             })
    #     return res
            
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id:
            return
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # If not seller, use the standard price. It needs a proper currency conversion.
        if not seller:
            #po_line_uom = self.product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                #self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.uom_id._compute_price(self.product_id.standard_price, self.product_id.uom_po_id),
                self.product_id.supplier_taxes_id,
                self.taxes_id,
                self.company_id,
            )
            if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
                price_unit = self.order_id.company_id.currency_id._convert(
                    price_unit,
                    self.order_id.currency_id,
                    self.order_id.company_id,
                    self.date_order or fields.Date.today(),
                )
            self.price_unit = price_unit
            #if self.order_id.apply_manual_currency_exchange:
             #   self.price_unit = price_unit * self.order_id.manual_currency_exchange_rate
            #else:
             #   if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
              #      price_unit = self.order_id.company_id.currency_id._convert(
               #         price_unit,
                #        self.order_id.currency_id,
                 #       self.order_id.company_id,
                  #      self.date_order or fields.Date.today(),
                   # )

                    #self.price_unit = price_unit
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, self.product_id.supplier_taxes_id, self.taxes_id, self.company_id) if seller else 0.0
        if self.order_id.apply_manual_currency_exchange:
            self.price_unit = (price_unit * self.order_id.manual_currency_exchange_rate) if self.order_id.manual_currency_exchange_rate > 0 else 0
            return
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        if self.order_id.apply_manual_currency_exchange:
            price_unit = (self.price_unit / self.order_id.manual_currency_exchange_rate) if self.order_id.manual_currency_exchange_rate > 0 else 0
        return super(PurchaseOrderLine,self)._prepare_stock_move_vals(picking,price_unit,product_uom_qty,product_uom)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        price = super(StockMove, self)._get_price_unit()
        if self.picking_id.purchase_id and self.picking_id.purchase_id.apply_manual_currency_exchange:
            price = self.price_unit
        return price
