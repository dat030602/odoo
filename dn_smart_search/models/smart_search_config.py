from odoo import api, fields, models


class SmartSearchConfig(models.Model):
    _name = "smart.search.config"
    _description = "Smart Search Configuration"
    _order = "priority, name, id"
    _rec_name = "name"
    _allow_sudo_commands = False

    name = fields.Char(required=True)
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade", index=True)
    model_name = fields.Char(related="model_id.model", store=True, readonly=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=100)
    search_field_names = fields.Char(required=True)
    subtitle_field_name = fields.Char()
    icon = fields.Char(default="fa-search")

    _sql_constraints = [
        (
            "smart_search_model_uniq",
            "unique(model_id)",
            "Only one configuration is allowed per model.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["smart.search"]._clear_cache()
        return records

    def write(self, vals):
        result = super().write(vals)
        self.env["smart.search"]._clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env["smart.search"]._clear_cache()
        return result

    @api.model
    def _ensure_default_configs(self):
        defaults = [
            ("sale.order", "Sale Orders", "name,client_order_ref,partner_id", "partner_id"),
            ("purchase.order", "Purchase Orders", "name,partner_ref,partner_id", "partner_id"),
            ("account.move", "Invoices", "name,ref,invoice_origin", "partner_id"),
            ("res.partner", "Contacts", "name,email,phone,ref", "email"),
            ("stock.picking", "Transfers", "name,origin,partner_id", "partner_id"),
            ("project.task", "Tasks", "name,description,partner_id", "partner_id"),
            ("product.product", "Products", "default_code,name,barcode", "default_code"),
        ]
        existing = {record.model_name for record in self.search([])}
        model_model = self.env["ir.model"]
        for model_name, label, fields_csv, subtitle_field in defaults:
            if model_name in existing:
                continue
            model = model_model.search([("model", "=", model_name)], limit=1)
            if not model:
                continue
            self.create(
                {
                    "name": label,
                    "model_id": model.id,
                    "search_field_names": fields_csv,
                    "subtitle_field_name": subtitle_field,
                    "icon": model_model._smart_search_default_icon(model_name),
                    "priority": 100,
                },
            )
