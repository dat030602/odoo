# ©  2008-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class ProductChangeUoM(models.TransientModel):
    _name = "product.change.uom"
    _description = "Product Change Uom"

    uom_id = fields.Many2one(
        "uom.uom",
        "Unit of Measure",
        required=True,
    )
    uom_po_id = fields.Many2one("uom.uom", "Purchase Unit of Measure", required=True)

    is_update_uom_sale = fields.Boolean('Update the unit of measure used on the sales order when the unit of inventory is different')
    uom_used_sale_id = fields.Many2one('uom.uom','Units used on sales order')
    uom_substitute_sale_id = fields.Many2one('uom.uom','Substitute unit on sales order')

    is_update_uom_purchase = fields.Boolean('Update the unit of measure used on the Purchases order when the unit of inventory is different')
    uom_used_purchase_id = fields.Many2one('uom.uom','Units used on purchases order')
    uom_substitute_purchase_id = fields.Many2one('uom.uom','Substitute unit on purchases order')

    @api.onchange("uom_id")
    def _onchange_uom_id(self):
        if self.uom_id:
            self.uom_po_id = self.uom_id.id

    @api.onchange("uom_po_id")
    def _onchange_uom(self):
        if self.uom_id and self.uom_po_id and self.uom_id.category_id != self.uom_po_id.category_id:
            self.uom_po_id = self.uom_id

    @api.model
    def default_get(self, fields_list):
        defaults = super(ProductChangeUoM, self).default_get(fields_list)
        context = self.env.context
        active_ids = context.get("active_ids", False)
        if active_ids:
            products = self.env[context.get("active_model")].browse(active_ids)
            if context.get("active_model") == 'product.product':
                variants = self.env["product.product"].browse(active_ids)
                product = variants.mapped('product_tmpl_id')
            
            uom_id = products.mapped("uom_id")
            uom_po_id = products.mapped("uom_po_id")

            if len(uom_id) >1 or len(uom_po_id) > 1:
                raise ValidationError('Có nhiều hơn một đơn vị được tìm thấy. Vui lòng kiểm tra lại')

            defaults["uom_id"] = uom_id.id
            defaults["uom_po_id"] = uom_po_id.id

        return defaults

    def do_change(self):
        context = self.env.context
        active_ids = context.get("active_ids", False)
        if active_ids:
            variants = False
            if context.get("active_model") == 'product.template':
                product = self.env["product.template"].browse(active_ids)
                variants = product.mapped('product_variant_ids')

            if context.get("active_model") == 'product.product':
                variant = self.env["product.product"].browse(active_ids)
                product = variant.mapped('product_tmpl_id')
                variants = product.mapped('product_variant_ids')

            if not variants:
                return 


            base_uom_id = product[:1].uom_id
            base_uom_po_id = product[:1].uom_po_id

            # Update đơn vị sử dụng trên đơn mua
            if self.is_update_uom_purchase:
                domain = [("product_id", "in", variants.ids), ("product_uom", "=", self.uom_used_purchase_id.id)]
                purchase_lines = self.env["purchase.order.line"].search(domain)
                if purchase_lines:
                    query_dic = {
                        "ids": tuple(purchase_lines.ids),
                        "product_uom": self.uom_substitute_purchase_id.id,
                    }
                    query = "UPDATE purchase_order_line SET product_uom = %(product_uom)s WHERE id in %(ids)s"
                    self._cr.execute(query, query_dic)

            # Update đơn vị sử dụng trên đơn bán
            if self.is_update_uom_sale:
                domain = [("product_id", "in", variants.ids), ("product_uom", "=", self.uom_used_sale_id.id)]
                sal_order_lines = self.env["sale.order.line"].search(domain)
                if sal_order_lines:
                    query_dic = {
                        "ids": tuple(sal_order_lines.ids),
                        "product_uom": self.uom_substitute_sale_id.id,
                    }
                    query = "UPDATE sale_order_line SET product_uom = %(product_uom)s WHERE id in %(ids)s"
                    self._cr.execute(query, query_dic)

            # inlocuire in comanda de achizitie
            domain = [("product_id", "in", variants.ids), ("product_uom", "=", base_uom_po_id.id)]
            purchase_lines = self.env["purchase.order.line"].search(domain)
            if purchase_lines:
                query_dic = {
                    "ids": tuple(purchase_lines.ids),
                    "product_uom": self.uom_po_id.id,
                }
                query = "UPDATE purchase_order_line SET product_uom = %(product_uom)s WHERE id in %(ids)s"
                self._cr.execute(query, query_dic)

            # inlocuire in comanda de vanzare
            domain = [("product_id", "in", variants.ids), ("product_uom", "=", base_uom_id.id)]
            sal_order_lines = self.env["sale.order.line"].search(domain)
            if sal_order_lines:
                query_dic = {
                    "ids": tuple(sal_order_lines.ids),
                    "product_uom": self.uom_id.id,
                }
                query = "UPDATE sale_order_line SET product_uom = %(product_uom)s WHERE id in %(ids)s"
                self._cr.execute(query, query_dic)

            # inlocuire in facturi
            domain = [("product_id", "in", variants.ids), ("product_uom_id", "=", base_uom_id.id)]
            account_lines = self.env["account.move.line"].search(domain)
            if account_lines:
                query_dic = {
                    "ids": tuple(account_lines.ids),
                    "product_uom_id": self.uom_id.id,
                }
                query = "UPDATE account_move_line SET product_uom_id = %(product_uom_id)s WHERE id in %(ids)s"
                self._cr.execute(query, query_dic)

            # inlocuire in miscari de stoc
            domain = [("product_id", "in", variants.ids), ("product_uom", "=", base_uom_id.id)]
            stock_moves = self.env["stock.move"].search(domain)
            if stock_moves:
                query_dic = {
                    "ids": tuple(stock_moves.ids),
                    "product_uom": self.uom_id.id,
                }
                query = "UPDATE stock_move SET product_uom = %(product_uom)s WHERE id in %(ids)s"
                self._cr.execute(query, query_dic)

            # inlocuire in miscari de stoc
            domain = [("product_id", "in", variants.ids), ("product_uom_id", "=", base_uom_id.id)]
            stock_move_lines = self.env["stock.move.line"].search(domain)
            if stock_move_lines:
                query_dic = {
                    "ids": tuple(stock_move_lines.ids),
                    "product_uom_id": self.uom_id.id,
                }
                query = "UPDATE stock_move_line SET product_uom_id = %(product_uom_id)s WHERE id in %(ids)s"
                self._cr.execute(query, query_dic)

            query_dic = {"ids": tuple(product.ids), "uom_id": self.uom_id.id, "uom_po_id": self.uom_po_id.id}
            query = "UPDATE product_template SET uom_id = %(uom_id)s, uom_po_id=%(uom_po_id)s  WHERE id in %(ids)s"
            self._cr.execute(query, query_dic)
