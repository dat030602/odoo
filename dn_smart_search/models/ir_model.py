from odoo import api, models


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def _smart_search_default_icon(self, model_name):
        icons = {
            "sale.order": "fa-shopping-cart",
            "purchase.order": "fa-shopping-basket",
            "account.move": "fa-file-text-o",
            "res.partner": "fa-user",
            "stock.picking": "fa-truck",
            "project.task": "fa-tasks",
            "product.product": "fa-cube",
        }
        return icons.get(model_name, "fa-search")

    @api.model
    def _smart_search_default_fields(self, model_name):
        defaults = {
            "sale.order": "name,client_order_ref,partner_id",
            "purchase.order": "name,partner_ref,partner_id",
            "account.move": "name,ref,invoice_origin",
            "res.partner": "name,email,phone,mobile,ref",
            "stock.picking": "name,origin,partner_id",
            "project.task": "name,description,partner_id",
            "product.product": "default_code,name,barcode",
        }
        return defaults.get(model_name, "name")
